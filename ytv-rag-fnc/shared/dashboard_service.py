"""Read-only, channel-scoped view models for the React dashboard."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .cosmos_repository import CosmosRepository
from .data_adapter import (
    normalize_channel_snapshot,
    normalize_evaluation,
    normalize_prediction,
    normalize_snapshot,
    normalize_video,
)


class DashboardAccessError(PermissionError):
    def __init__(self, message: str, status_code: int = 403, code: str = "CHANNEL_ACCESS_DENIED") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _growth(previous: Any, current: Any) -> float | None:
    start = _number(previous)
    end = _number(current)
    if start in (None, 0) or end is None:
        return None
    return round((end - start) / start * 100, 2)


def _elapsed_hours(start_value: Any, end_value: Any) -> float | None:
    if not isinstance(start_value, str) or not isinstance(end_value, str):
        return None
    try:
        start = datetime.fromisoformat(start_value.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(0.0, (end - start).total_seconds() / 3600)


def _latest_by(rows: list[dict[str, Any]], key: str, time_key: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        identifier = str(row.get(key) or "")
        if not identifier:
            continue
        if identifier not in latest or str(row.get(time_key) or "") >= str(latest[identifier].get(time_key) or ""):
            latest[identifier] = row
    return latest


class DashboardService:
    def __init__(self, repository: Any | None = None, now_provider: Any | None = None) -> None:
        self.repository = repository or CosmosRepository()
        self.now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def channel_scope(user: dict[str, Any], requested_channel_id: str = "") -> str:
        own_channel_id = str(user.get("channel_id") or "").strip()
        requested = str(requested_channel_id or "").strip()
        if user.get("role") == "admin":
            if not requested:
                raise DashboardAccessError("관리자는 조회할 채널 ID를 지정해 주세요.", 400, "CHANNEL_REQUIRED")
            return requested
        if not own_channel_id:
            raise DashboardAccessError("연결된 채널 데이터가 없습니다.", 403, "CHANNEL_NOT_CONNECTED")
        if requested and requested != own_channel_id:
            raise DashboardAccessError("다른 채널의 데이터는 조회할 수 없습니다.")
        return own_channel_id

    def _channel_bundle(self, channel_id: str) -> dict[str, Any]:
        channel = self.repository.get_channel(channel_id)
        if not channel:
            raise DashboardAccessError("채널 데이터를 찾을 수 없습니다.", 404, "CHANNEL_NOT_FOUND")

        channel_snapshots = sorted(
            [normalize_channel_snapshot(row) for row in self.repository.get_channel_snapshots(channel_id, limit=200)],
            key=lambda row: str(row.get("snapshot_time") or ""),
        )
        videos = [
            normalized
            for row in self.repository.list_channel_videos(channel_id, limit=100)
            if (normalized := normalize_video(row))
        ]
        predictions = [
            normalized
            for row in self.repository.list_channel_predictions(channel_id, limit=200)
            if (normalized := normalize_prediction(row))
        ]
        labels = [
            normalized
            for row in self.repository.list_channel_labels(channel_id, limit=200)
            if (normalized := normalize_evaluation(row))
        ]
        video_snapshots = [
            normalize_snapshot(row)
            for row in self.repository.list_channel_video_snapshots(channel_id, limit=500)
        ]
        return {
            "channel": channel,
            "channel_snapshots": channel_snapshots,
            "videos": videos,
            "predictions": predictions,
            "labels": labels,
            "video_snapshots": video_snapshots,
        }

    def video_metadata(self, video_id: str) -> dict[str, Any]:
        normalized_id = str(video_id or "").strip()
        if not normalized_id:
            raise DashboardAccessError(
                "영상 ID를 입력해 주세요.", 400, "VIDEO_ID_REQUIRED"
            )

        video = normalize_video(self.repository.get_video(normalized_id))
        if not video:
            return {"found": False, "video_id": normalized_id}

        return {
            "found": True,
            "video_id": video.get("video_id") or normalized_id,
            "title": video.get("title"),
            "thumbnail_url": video.get("thumbnail_url"),
        }

    @staticmethod
    def _video_rows(bundle: dict[str, Any]) -> list[dict[str, Any]]:
        prediction_by_video = _latest_by(bundle["predictions"], "video_id", "predicted_at")
        label_by_video = _latest_by(bundle["labels"], "video_id", "evaluated_at")
        snapshot_by_video = _latest_by(bundle["video_snapshots"], "video_id", "collected_at")
        snapshots_by_video: dict[str, list[dict[str, Any]]] = {}
        for snapshot_row in bundle["video_snapshots"]:
            snapshot_video_id = str(snapshot_row.get("video_id") or "")
            if snapshot_video_id:
                snapshots_by_video.setdefault(snapshot_video_id, []).append(snapshot_row)
        rows = []
        for video in sorted(bundle["videos"], key=lambda row: str(row.get("published_at") or ""), reverse=True):
            video_id = str(video.get("video_id") or "")
            prediction = prediction_by_video.get(video_id, {})
            label = label_by_video.get(video_id, {})
            snapshot = snapshot_by_video.get(video_id, {})
            video_snapshots = snapshots_by_video.get(video_id, [])
            tracking_hour_values = [
                hours
                for row in video_snapshots
                for hours in (
                    _number(row.get("target_age_hours")),
                    _number(row.get("actual_age_hours")),
                    _elapsed_hours(video.get("published_at"), row.get("collected_at")),
                )
                if hours is not None
            ]
            label_target_hours = _number(label.get("evaluation_target_hours"))
            if label_target_hours is not None:
                tracking_hour_values.append(label_target_hours)
            tracking_hours = max(tracking_hour_values) if tracking_hour_values else None
            views = _number(snapshot.get("view_count"))
            likes = _number(snapshot.get("like_count"))
            comments = _number(snapshot.get("comment_count"))
            engagement_rate = None
            if views and likes is not None and comments is not None:
                engagement_rate = round((likes + comments) / views * 100, 2)
            rows.append(
                {
                    "video_id": video_id,
                    "title": video.get("title") or "제목 없음",
                    "published_at": video.get("published_at"),
                    "thumbnail_url": video.get("thumbnail_url"),
                    "video_url": video.get("video_url") or (f"https://www.youtube.com/watch?v={video_id}" if video_id else None),
                    "content_domain": video.get("content_domain") or video.get("project_category"),
                    "view_count": views,
                    "like_count": likes,
                    "comment_count": comments,
                    "engagement_rate": engagement_rate,
                    "viral_score": _number(prediction.get("viral_score")),
                    "performance_multiplier": _number(prediction.get("expected_performance_multiplier")),
                    "rank": prediction.get("rank"),
                    "label_score": _number(label.get("label_score")),
                    "has_prediction": bool(prediction),
                    "has_label": bool(label),
                    "has_snapshot": bool(snapshot),
                    "snapshot_count": len(video_snapshots),
                    "tracking_hours": round(tracking_hours, 1) if tracking_hours is not None else None,
                    "has_72h_tracking": bool(label) or bool(tracking_hours is not None and tracking_hours >= 72),
                }
            )
        return rows

    def channel_summary(self, user: dict[str, Any], requested_channel_id: str = "") -> dict[str, Any]:
        channel_id = self.channel_scope(user, requested_channel_id)
        bundle = self._channel_bundle(channel_id)
        snapshots = bundle["channel_snapshots"]
        latest = snapshots[-1] if snapshots else {}
        earliest = snapshots[0] if snapshots else {}
        videos = self._video_rows(bundle)
        engagement_values = [row["engagement_rate"] for row in videos if row["engagement_rate"] is not None]
        channel = bundle["channel"]
        custom_url = str(channel.get("channel_custom_url") or channel.get("custom_url") or "").strip()
        channel_url = channel.get("channel_url")
        if not channel_url and custom_url:
            channel_url = f"https://www.youtube.com/{custom_url.lstrip('/')}"
        if not channel_url and channel_id:
            channel_url = f"https://www.youtube.com/channel/{channel_id}"
        return {
            "channel_id": channel_id,
            "channel_title": channel.get("channel_title") or user.get("channel_title"),
            "channel_thumbnail_url": (
                channel.get("channel_thumbnail_url")
                or channel.get("thumbnail_high_url")
                or channel.get("thumbnail_medium_url")
                or channel.get("thumbnail_default_url")
            ),
            "channel_url": channel_url,
            "project_category": channel.get("project_category"),
            "subscriber_count": _number(latest.get("subscriber_count")),
            "total_view_count": _number(latest.get("view_count")),
            "video_count": int(_number(latest.get("video_count")) or len(videos)),
            "subscriber_growth_rate": _number(latest.get("subscriber_growth_rate")) if latest.get("subscriber_growth_rate") is not None else _growth(earliest.get("subscriber_count"), latest.get("subscriber_count")),
            "view_growth_rate": _number(latest.get("view_growth_rate")) if latest.get("view_growth_rate") is not None else _growth(earliest.get("view_count"), latest.get("view_count")),
            "average_engagement_rate": round(sum(engagement_values) / len(engagement_values), 2) if engagement_values else None,
            "prediction_count": len(bundle["predictions"]),
            "label_count": len(bundle["labels"]),
            "snapshot_count": len(bundle["video_snapshots"]),
            "period_start": earliest.get("snapshot_time"),
            "period_end": latest.get("snapshot_time"),
            "recent_videos": videos[:8],
        }

    def videos(self, user: dict[str, Any], requested_channel_id: str = "") -> dict[str, Any]:
        channel_id = self.channel_scope(user, requested_channel_id)
        bundle = self._channel_bundle(channel_id)
        return {"channel_id": channel_id, "videos": self._video_rows(bundle)}

    def _top_video_ranking(
        self, channel_rows: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """Recent scored videos ranked by viral score, with channel context attached.

        The frontend filters by category/channel first and then re-ranks, so this
        must not pre-cut to a top N — sorting order is kept as a convenience only.
        """
        korea_timezone = timezone(timedelta(hours=9))
        today = self.now_provider().astimezone(korea_timezone).date()
        cutoff_date = today - timedelta(days=7)
        predictions = sorted(
            (
                normalized
                for row in self.repository.list_predictions(limit=None)
                if (normalized := normalize_prediction(row))
                and normalized.get("viral_score") is not None
            ),
            key=lambda row: row["viral_score"],
            reverse=True,
        )

        channels = {
            str(row.get("channel_id")): row
            for row in (
                channel_rows
                if channel_rows is not None
                else self.repository.list_channels(limit=None)
            )
            if row.get("channel_id")
        }

        ranking = []
        for prediction in predictions:
            video_id = str(prediction.get("video_id") or "")
            video = normalize_video(self.repository.get_video(video_id)) if video_id else None
            if not video:
                continue
            published_value = video.get("published_at")
            try:
                published_at = datetime.fromisoformat(
                    str(published_value).replace("Z", "+00:00")
                )
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
                published_date = published_at.astimezone(korea_timezone).date()
            except (TypeError, ValueError):
                continue
            if published_date < cutoff_date or published_date > today:
                continue
            channel = channels.get(str(video.get("channel_id") or ""), {})
            total_views = _number(video.get("channel_total_view_count"))
            video_count = _number(video.get("public_video_count"))
            avg_view_count = (
                round(total_views / video_count, 1) if total_views and video_count else None
            )
            ranking.append(
                {
                    "video_id": video.get("video_id"),
                    "title": video.get("title") or "제목 없음",
                    "thumbnail_url": video.get("thumbnail_url"),
                    "published_at": published_value,
                    "category": (
                        channel.get("project_category")
                        or video.get("project_category")
                        or video.get("content_domain")
                    ),
                    "viral_score": prediction.get("viral_score"),
                    "channel_id": video.get("channel_id"),
                    "channel_title": channel.get("channel_title") or video.get("channel_title"),
                    "channel_thumbnail_url": (
                        channel.get("channel_thumbnail_url")
                        or channel.get("thumbnail_high_url")
                        or channel.get("thumbnail_medium_url")
                        or channel.get("thumbnail_default_url")
                    ),
                    "subscriber_count": (
                        _number(channel.get("subscriber_count"))
                        if channel.get("subscriber_count") is not None
                        else _number(video.get("subscriber_count"))
                    ),
                    "avg_view_count": avg_view_count,
                }
            )
        return ranking

    @staticmethod
    def _channel_benchmarks(
        channel_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        benchmarks = []
        for channel in channel_rows:
            channel_id = str(channel.get("channel_id") or "").strip()
            if not channel_id:
                continue
            benchmarks.append(
                {
                    "channel_id": channel_id,
                    "channel_title": channel.get("channel_title") or "채널명 없음",
                    "channel_thumbnail_url": (
                        channel.get("channel_thumbnail_url")
                        or channel.get("thumbnail_high_url")
                        or channel.get("thumbnail_medium_url")
                        or channel.get("thumbnail_default_url")
                    ),
                    "project_category": channel.get("project_category"),
                    "subscriber_count": _number(channel.get("subscriber_count")),
                }
            )
        return sorted(
            benchmarks,
            key=lambda row: row["subscriber_count"]
            if row["subscriber_count"] is not None
            else -1,
            reverse=True,
        )

    def admin_overview(self, user: dict[str, Any]) -> dict[str, Any]:
        counts = self.repository.admin_counts()
        categories = self.repository.channel_category_counts()
        channel_rows = self.repository.list_channels(limit=None)
        video_count = counts["videos"]
        return {
            "stats": {
                "channel_count": counts["channels"],
                "video_count": video_count,
                "prediction_count": counts["predictions"],
                "label_count": counts["labels"],
                "snapshot_count": counts["video_snapshots"],
                "user_count": counts["users"],
                "prediction_coverage": round(counts["predicted_videos"] / video_count * 100, 1) if video_count else None,
                "label_coverage": round(counts["labeled_videos"] / video_count * 100, 1) if video_count else None,
            },
            "categories": [
                {**row, "status": "active"}
                for row in sorted(categories, key=lambda item: str(item.get("name") or ""))
            ],
            "channel_benchmarks": self._channel_benchmarks(channel_rows),
            "video_ranking": self._top_video_ranking(channel_rows),
        }
