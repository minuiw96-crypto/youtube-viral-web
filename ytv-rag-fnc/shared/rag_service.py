"""Personalized hybrid RAG orchestration."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from .answer_context import RESPONSE_CONTRACT, build_evidence_summary
from .cosmos_repository import CosmosRepository
from .data_adapter import (
    normalize_evaluation,
    normalize_channel_snapshot,
    normalize_prediction,
    normalize_snapshot,
    normalize_video,
)
from .knowledge_base import embedding_text, lexical_search, seed_documents
from .openai_service import create_answer, create_embedding, create_embeddings
from .metrics import calculate_context_metrics
from .question_analyzer import GENERIC_CHANNEL_QUALIFIERS, analyze_question
from .search_normalization import search_tokens
from .settings import Settings


LOGGER = logging.getLogger(__name__)


CATEGORY_REQUIREMENTS = {
    "channel_growth": {"channel", "channel_snapshots", "videos"},
    "video_list": {"videos"},
    "video_performance": {"videos", "selected_video", "selected_snapshots"},
    "prediction_score": {
        "videos",
        "selected_video",
        "selected_prediction",
        "channel_predictions",
    },
    "shap_factors": {"videos", "selected_video", "selected_prediction"},
    "prediction_vs_actual": {
        "videos",
        "selected_video",
        "selected_prediction",
        "selected_snapshots",
        "selected_evaluation",
    },
    "video_ranking": {
        "videos",
        "channel_predictions",
        "channel_labels",
        "channel_video_snapshots",
    },
    "model_evaluation": {
        "videos",
        "channel_predictions",
        "channel_labels",
    },
    "channel_baseline_comparison": {
        "videos",
        "selected_video",
        "selected_prediction",
        "selected_snapshots",
        "selected_evaluation",
        "channel_predictions",
        "channel_labels",
        "channel_video_snapshots",
    },
    "data_status": {
        "channel",
        "channel_snapshots",
        "videos",
        "channel_predictions",
        "channel_labels",
        "channel_video_snapshots",
    },
    "glossary_model": set(),
}

VIDEO_REQUIRED_CATEGORIES = {
    "video_performance",
    "prediction_score",
    "shap_factors",
    "prediction_vs_actual",
    "channel_baseline_comparison",
}


class ChannelAccessError(ValueError):
    """Raised when a requested video is outside the active channel scope."""

    def __init__(
        self,
        message: str,
        code: str = "CHANNEL_ACCESS_DENIED",
    ) -> None:
        super().__init__(message)
        self.code = code


def _number(value: Any, default: float = -1.0) -> float:
    return float(value) if isinstance(value, (int, float)) else default


def _match_video(question: str, videos: list[dict[str, Any]]) -> str | None:
    lowered = question.lower()
    for video in videos:
        video_id = str(video.get("video_id") or "")
        title = str(video.get("title") or "")
        if video_id and video_id.lower() in lowered:
            return video_id
        if title and title.lower() in lowered:
            return video_id

    # search_tokens() normalizes spacing/particles the same way for the question
    # and each title, so a query written without spaces (e.g. "연평도1편") still
    # matches a title stored with spaces (e.g. "연평도 1편").
    question_tokens = search_tokens(question)
    best: tuple[int, str | None] = (0, None)
    best_count = 0
    for video in videos:
        title_tokens = search_tokens(video.get("title"))
        score = len(question_tokens & title_tokens)
        if score > best[0]:
            best = (score, video.get("video_id"))
            best_count = 1
        elif score > 0 and score == best[0]:
            best_count += 1
    return best[1] if best[0] >= 1 and best_count == 1 else None


class RagService:
    def __init__(
        self,
        settings: Settings | None = None,
        repository: CosmosRepository | None = None,
    ) -> None:
        self.settings = settings or Settings.from_environment()
        self.repository = repository

    def resolve_channel_scope(
        self, body: dict[str, Any], user: dict[str, Any]
    ) -> tuple[str, str]:
        role = str(user.get("role") or "user")
        if role == "admin":
            requested = str(body.get("channel_id") or "").strip()
            if not requested:
                return "", "admin_unscoped"
            if not self._repository().get_channel(requested):
                raise ChannelAccessError(
                    "선택한 채널을 찾을 수 없습니다.",
                    "CHANNEL_NOT_FOUND",
                )
            return requested, "admin_selected"

        channel_id = str(user.get("channel_id") or "").strip()
        if not channel_id:
            raise ChannelAccessError(
                "연결된 YouTube 채널이 없습니다.",
                "CHANNEL_NOT_ASSIGNED",
            )
        return channel_id, "authenticated_user"

    def _repository(self) -> CosmosRepository:
        if self.repository is None:
            self.repository = CosmosRepository(self.settings)
        return self.repository

    @staticmethod
    def _normalized_channel_name(value: Any) -> str:
        normalized = re.sub(r"\s+", "", str(value or "").strip().lower())
        return normalized[:-2] if normalized.endswith("채널") else normalized

    def enforce_question_scope(
        self,
        analysis: dict[str, Any],
        user: dict[str, Any],
        active_channel_id: str,
        question: str,
    ) -> None:
        """Reject only channel references explicitly present in the user question."""
        if str(user.get("role") or "user") == "admin":
            return

        active = self._normalized_channel_name(active_channel_id)
        for channel_id in re.findall(r"\bUC[0-9A-Za-z_-]{6,}\b", question):
            if self._normalized_channel_name(channel_id) != active:
                raise ChannelAccessError(
                    "다른 채널의 데이터는 조회할 수 없습니다.",
                    "CHANNEL_FORBIDDEN",
                )

        requested = self._normalized_channel_name(analysis.get("channel_reference"))
        if not requested or requested in GENERIC_CHANNEL_QUALIFIERS:
            return
        allowed = {
            active,
            self._normalized_channel_name(user.get("channel_title")),
            self._normalized_channel_name(user.get("channel_input")),
        }
        allowed.discard("")
        if requested in allowed:
            return

        # A model can mistake a video ID or title for a channel reference. Only
        # trust the extraction when the original question names it as a channel.
        compact_question = re.sub(r"\s+", "", question.lower())
        explicitly_named = f"{requested}채널" in compact_question
        if not explicitly_named:
            return
        raise ChannelAccessError(
            "다른 채널의 데이터는 조회할 수 없습니다.",
            "CHANNEL_FORBIDDEN",
        )

    def _knowledge(self, question: str, channel_id: str) -> tuple[list[dict[str, Any]], str]:
        if self.settings.vector_search_ready and channel_id:
            try:
                embedding = create_embedding(question)
                documents = self._repository().vector_search(embedding, channel_id)
                if documents:
                    return documents, "embedding_cosine"
                LOGGER.warning("Embedding search returned no indexed documents; using lexical fallback.")
            except Exception:
                LOGGER.exception("Vector search failed; using the built-in knowledge fallback.")
        local_search = getattr(self._repository(), "lexical_search", None)
        if callable(local_search):
            documents = local_search(question, channel_id)
            if documents:
                return documents, "local_json_lexical"
        return lexical_search(question), "built_in_lexical"

    def _video_context(
        self,
        video_id: str,
        channel_id: str,
        *,
        include_prediction: bool = True,
        include_snapshots: bool = True,
        include_evaluation: bool = True,
    ) -> dict[str, Any]:
        repository = self._repository()
        video = normalize_video(repository.get_video(video_id))
        if not video:
            raise ValueError("선택한 영상을 찾을 수 없습니다.")
        if channel_id and video.get("channel_id") != channel_id:
            raise ChannelAccessError(
                "현재 채널에서 해당 영상을 찾을 수 없습니다.",
                "CHANNEL_FORBIDDEN",
            )

        prediction = (
            normalize_prediction(repository.get_latest_prediction(video_id))
            if include_prediction or include_evaluation
            else None
        )
        snapshots = (
            [normalize_snapshot(row) for row in repository.get_snapshots(video_id)]
            if include_snapshots
            else None
        )
        evaluation = (
            normalize_evaluation(
                repository.get_evaluation(
                    video_id,
                    prediction.get("candidate_batch_id") if prediction else None,
                )
            )
            if include_evaluation
            else None
        )
        context = {"video": video}
        if include_prediction:
            context["prediction"] = prediction
        if include_snapshots:
            context["snapshots"] = snapshots
        if include_evaluation:
            context["evaluation"] = evaluation
        return context

    def _list_channel_videos(self, channel_id: str) -> list[dict[str, Any]]:
        videos = [
            normalize_video(row)
            for row in self._repository().list_channel_videos(channel_id, limit=50)
        ]
        videos = [video for video in videos if video]
        videos.sort(
            key=lambda video: str(
                video.get("published_at") or video.get("first_collected_at") or ""
            ),
            reverse=True,
        )
        return videos

    @staticmethod
    def _latest_by_video(
        rows: list[dict[str, Any]],
        *time_fields: str,
    ) -> dict[str, dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        for row in rows:
            video_id = str(row.get("video_id") or "")
            if not video_id:
                continue
            row_time = max((str(row.get(field) or "") for field in time_fields), default="")
            existing = latest.get(video_id)
            existing_time = (
                max((str(existing.get(field) or "") for field in time_fields), default="")
                if existing
                else ""
            )
            if not existing or row_time >= existing_time:
                latest[video_id] = row
        return latest

    def _batch_predictions(
        self, channel_id: str, videos: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        rows = self._repository().list_channel_predictions(channel_id, limit=100)
        if rows:
            return rows
        return [
            row
            for video in videos[:20]
            if (row := self._repository().get_latest_prediction(str(video.get("video_id"))))
        ]

    def _batch_labels(
        self, channel_id: str, videos: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        rows = self._repository().list_channel_labels(channel_id, limit=100)
        if rows:
            return rows
        return [
            row
            for video in videos[:20]
            if (
                row := self._repository().get_evaluation(
                    str(video.get("video_id")),
                    None,
                )
            )
        ]

    def _batch_video_snapshots(
        self, channel_id: str, videos: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        rows = self._repository().list_channel_video_snapshots(channel_id, limit=300)
        if rows:
            return rows
        snapshots = []
        for video in videos[:20]:
            snapshots.extend(
                self._repository().get_snapshots(str(video.get("video_id")), limit=100)
            )
        return snapshots

    def _channel_context(
        self,
        channel_id: str,
        selected_video_id: str | None,
        question: str,
        question_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        categories = [question_analysis.get("primary_category") or "video_performance"]
        categories.extend(question_analysis.get("secondary_categories") or [])
        categories = list(dict.fromkeys(categories))
        requirements: set[str] = set()
        for category in categories:
            requirements.update(CATEGORY_REQUIREMENTS.get(category, set()))

        base_context: dict[str, Any] = {
            "channel_id": channel_id,
            "primary_category": categories[0],
            "categories": categories,
            "data_sources": [],
            "selected_video": None,
            "needs_clarification": False,
            "clarification_question": None,
        }
        if not requirements:
            return base_context

        repository = self._repository()
        if "channel" in requirements:
            base_context["channel"] = repository.get_channel(channel_id)
            base_context["data_sources"].append("channels")
        if "channel_snapshots" in requirements:
            base_context["channel_snapshots"] = [
                normalize_channel_snapshot(row)
                for row in repository.get_channel_snapshots(channel_id, limit=100)
            ]
            base_context["data_sources"].append("channel_snapshots")

        videos = self._list_channel_videos(channel_id) if "videos" in requirements else []
        if "videos" in requirements:
            base_context["data_sources"].append("videos")
            base_context["total_video_count"] = len(videos)

        selected_video_id = selected_video_id or _match_video(question, videos)
        if not selected_video_id and any(word in question for word in ("최근 영상", "최신 영상")):
            selected_video_id = str(videos[0].get("video_id")) if videos else None

        if set(categories) & VIDEO_REQUIRED_CATEGORIES and not selected_video_id:
            base_context["needs_clarification"] = True
            base_context["clarification_question"] = (
                "어느 영상을 분석할지 영상 제목이나 video_id를 알려주세요."
            )
            base_context["available_videos"] = [
                {"video_id": video.get("video_id"), "title": video.get("title")}
                for video in videos[:10]
            ]
            return base_context

        if selected_video_id and "selected_video" in requirements:
            selected = self._video_context(
                selected_video_id,
                channel_id,
                include_prediction="selected_prediction" in requirements,
                include_snapshots="selected_snapshots" in requirements,
                include_evaluation="selected_evaluation" in requirements,
            )
            base_context["selected_video"] = selected
            if "selected_prediction" in requirements:
                base_context["data_sources"].append("predictions")
            if "selected_snapshots" in requirements:
                base_context["data_sources"].append("video_snapshots")
            if "selected_evaluation" in requirements:
                base_context["data_sources"].append("labels")

        expose_videos = bool(
            {"channel_growth", "video_list", "video_ranking", "channel_baseline_comparison", "data_status"}
            & set(categories)
        )
        if expose_videos:
            base_context["videos"] = videos[:30]
            base_context["video_count_in_context"] = len(videos)

        predictions = []
        labels = []
        video_snapshots = []
        if "channel_predictions" in requirements:
            predictions = self._batch_predictions(channel_id, videos)
            base_context["data_sources"].append("predictions")
        if "channel_labels" in requirements:
            labels = self._batch_labels(channel_id, videos)
            base_context["data_sources"].append("labels")
        if "channel_video_snapshots" in requirements:
            video_snapshots = self._batch_video_snapshots(channel_id, videos)
            base_context["data_sources"].append("video_snapshots")

        prediction_by_video = self._latest_by_video(predictions, "predicted_at")
        label_by_video = self._latest_by_video(labels, "calculated_at", "evaluated_at")
        snapshot_by_video = self._latest_by_video(
            video_snapshots, "snapshot_time", "collected_at", "target_age_hours"
        )

        if {"video_ranking", "model_evaluation"} & set(categories):
            base_context["ranking_candidates"] = [
                {
                    "video": video,
                    "prediction": normalize_prediction(
                        prediction_by_video.get(str(video.get("video_id")))
                    ),
                    "evaluation": normalize_evaluation(
                        label_by_video.get(str(video.get("video_id")))
                    ),
                    "latest_snapshot": (
                        normalize_snapshot(snapshot_by_video[str(video.get("video_id"))])
                        if str(video.get("video_id")) in snapshot_by_video
                        else None
                    ),
                }
                for video in videos[:30]
            ]

        if predictions:
            prediction_cohort = []
            for video in videos[:30]:
                prediction = normalize_prediction(
                    prediction_by_video.get(str(video.get("video_id")))
                )
                if prediction and prediction.get("viral_score") is not None:
                    prediction_cohort.append(
                        {
                            "video_id": video.get("video_id"),
                            "title": video.get("title"),
                            "viral_score": prediction.get("viral_score"),
                        }
                    )
            base_context["prediction_cohort"] = prediction_cohort

        if "channel_baseline_comparison" in categories:
            base_context["comparison_videos"] = [
                {
                    "video": video,
                    "prediction": normalize_prediction(
                        prediction_by_video.get(str(video.get("video_id")))
                    ),
                    "evaluation": normalize_evaluation(
                        label_by_video.get(str(video.get("video_id")))
                    ),
                    "latest_snapshot": (
                        normalize_snapshot(snapshot_by_video[str(video.get("video_id"))])
                        if str(video.get("video_id")) in snapshot_by_video
                        else None
                    ),
                }
                for video in videos[:30]
            ]

        if "data_status" in categories:
            snapshot_counts: dict[str, int] = {}
            for row in video_snapshots:
                video_id = str(row.get("video_id") or "")
                if video_id:
                    snapshot_counts[video_id] = snapshot_counts.get(video_id, 0) + 1
            base_context["data_status"] = {
                "channel_document_present": bool(base_context.get("channel")),
                "channel_snapshot_count": len(base_context.get("channel_snapshots") or []),
                "video_count": len(videos),
                "prediction_document_count": len(predictions),
                "label_document_count": len(labels),
                "video_snapshot_document_count": len(video_snapshots),
                "videos": [
                    {
                        "video_id": video.get("video_id"),
                        "title": video.get("title"),
                        "has_prediction": str(video.get("video_id")) in prediction_by_video,
                        "has_label": str(video.get("video_id")) in label_by_video,
                        "snapshot_count": snapshot_counts.get(str(video.get("video_id")), 0),
                    }
                    for video in videos[:30]
                ],
            }

        base_context["data_sources"] = sorted(set(base_context["data_sources"]))
        return base_context

    def answer(self, body: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        question = str(body.get("question") or "").strip()
        channel_id, scope_source = self.resolve_channel_scope(body, user)
        question_analysis = analyze_question(question)
        selected_video_id = (
            str(body.get("video_id") or "").strip()
            or str(question_analysis.get("video_id") or "").strip()
            or None
        )
        conversation_video_id = str(body.get("context_video_id") or "").strip() or None

        categories = {question_analysis.get("primary_category")}
        categories.update(question_analysis.get("secondary_categories") or [])
        if (
            not selected_video_id
            and channel_id
            and categories & VIDEO_REQUIRED_CATEGORIES
            and (self.repository is not None or self.settings.cosmos_ready)
        ):
            videos = self._list_channel_videos(channel_id)
            video_hint = str(question_analysis.get("video_title") or "").strip()
            selected_video_id = (
                _match_video(video_hint, videos) if video_hint else None
            ) or _match_video(question, videos)
            if not selected_video_id and conversation_video_id:
                selected_video_id = conversation_video_id
            if selected_video_id:
                question_analysis = {
                    **question_analysis,
                    "needs_clarification": False,
                    "clarification_question": None,
                }

        self.enforce_question_scope(question_analysis, user, channel_id, question)

        if question_analysis.get("needs_clarification"):
            return {
                "answer": question_analysis.get("clarification_question")
                or "분석할 대상을 조금 더 구체적으로 알려주세요.",
                "personalization": {
                    "channel_id": channel_id or None,
                    "source": scope_source,
                    "role": user.get("role", "user"),
                    "is_personalized": False,
                },
                "question_analysis": question_analysis,
                "retrieval_mode": "not_started",
                "selected_video_id": None,
                "warnings": [],
            }

        channel_context = None
        warnings = []
        if channel_id and self.settings.cosmos_ready:
            channel_context = self._channel_context(
                channel_id,
                selected_video_id,
                question,
                question_analysis,
            )
        else:
            warnings.append(
                "채널 범위 또는 Cosmos DB가 설정되지 않아 공통 설명 자료만 사용했습니다."
            )

        if channel_context and channel_context.get("needs_clarification"):
            return {
                "answer": channel_context.get("clarification_question"),
                "personalization": {
                    "channel_id": channel_id or None,
                    "source": scope_source,
                    "role": user.get("role", "user"),
                    "is_personalized": False,
                },
                "question_analysis": question_analysis,
                "retrieval_mode": "not_started",
                "selected_video_id": None,
                "warnings": [],
            }

        computed_metrics = calculate_context_metrics(
            channel_context,
            question_analysis,
        )
        if channel_context is not None:
            channel_context["computed_metrics"] = computed_metrics

        knowledge, retrieval_mode = self._knowledge(question, channel_id)

        evidence_summary = build_evidence_summary(
            channel_context,
            question_analysis,
            computed_metrics,
            knowledge,
            retrieval_mode,
        )

        context = {
            "scope": {
                "channel_id": channel_id or None,
                "source": scope_source,
                "role": user.get("role", "user"),
                "is_personalized": bool(
                    channel_context and channel_context.get("data_sources")
                ),
            },
            "channel_data": channel_context,
            "question_analysis": question_analysis,
            "computed_metrics": computed_metrics,
            "knowledge": knowledge,
            "evidence_summary": evidence_summary,
            "response_contract": RESPONSE_CONTRACT,
            "warnings": warnings,
        }
        answer = create_answer(
            question,
            json.dumps(context, ensure_ascii=False, default=str),
        )
        return {
            "answer": answer,
            "personalization": context["scope"],
            "retrieval_mode": retrieval_mode,
            "question_analysis": question_analysis,
            "computed_metrics": computed_metrics,
            "evidence_summary": evidence_summary,
            "selected_video_id": (
                channel_context.get("selected_video", {}).get("video", {}).get("video_id")
                if channel_context and channel_context.get("selected_video")
                else selected_video_id
            ),
            "warnings": warnings,
        }

    def index_seed_knowledge(self) -> dict[str, Any]:
        if not self.settings.vector_search_ready:
            raise RuntimeError(
                "Cosmos DB와 AZURE_OPENAI_EMBEDDING_DEPLOYMENT 설정이 필요합니다."
            )
        documents = seed_documents()
        embeddings = create_embeddings([embedding_text(document) for document in documents])
        indexed = []
        dimensions = 0
        for document, embedding in zip(documents, embeddings):
            dimensions = len(embedding)
            stored = {
                **document,
                "embedding_model": self.settings.embedding_deployment,
                "embedding_dimensions": len(embedding),
                "contentVector": embedding,
            }
            self._repository().upsert_rag_document(stored)
            indexed.append(document["id"])
        return {
            "status": "ok",
            "indexed_count": len(indexed),
            "embedding_model": self.settings.embedding_deployment,
            "embedding_dimensions": dimensions,
            "ids": indexed,
        }
