"""Global formatting and validation rules for every user-facing RAG answer."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from .search_normalization import content_tokens


LOGGER = logging.getLogger(__name__)


DETAIL_REQUEST_TERMS = (
    "자세히",
    "상세히",
    "계산식",
    "계산 과정",
    "근거",
    "출처",
    "원본 데이터",
    "원본값",
)

INTERNAL_TERM_REPLACEMENTS = {
    "computed_metrics": "계산 결과",
    "evidence_summary": "근거 정보",
    "operational_data_sources": "확인한 데이터 출처",
    "local_explanation.method": "설명 방식",
    "synthetic_shap_like": "설명용 합성 피처 영향도",
    "channel_snapshots": "채널 시점별 통계",
    "video_snapshots": "영상 시점별 통계",
    # Other top-level keys of the context JSON handed to create_answer
    # (rag_service.answer()'s `context` dict) that the model can echo bare.
    "channel_data": "채널 데이터",
    "question_analysis": "질문 분석 결과",
    "response_contract": "답변 규칙",
    "scope": "적용 범위",
    "warnings": "주의사항",
    # Bare Cosmos container / data_sources names (rag_service.py appends these
    # exact strings to base_context["data_sources"]) — the compound forms
    # above (channel_snapshots, video_snapshots) are covered, but the model
    # sometimes echoes these plain container names directly.
    "channels": "채널 정보",
    "videos": "영상 데이터",
    "predictions": "예측 데이터",
    "labels": "실제 성과 데이터",
    # resolve_channel_scope()'s scope_source values.
    "authenticated_user": "로그인한 사용자",
    "admin_unscoped": "관리자 권한(채널 미지정)",
    "admin_selected": "관리자가 선택한 채널",
    "prediction_coverage": "예측 데이터 보유 비율",
    "label_coverage": "실제 성과 데이터 보유 비율",
    "snapshot_coverage": "시점별 통계 보유 비율",
    "video_count_in_context": "확인된 영상 수",
    "viral_score": "바이럴 점수",
    "predicted_score": "예측 점수",
    "label_score": "게시 후 3일 실제 성과 점수",
    "views_1h_log": "게시 후 1시간 조회수 신호",
    "views_6h_log": "게시 후 6시간 조회수 신호",
    "engagement_rate": "참여율",
    "view_velocity": "조회 증가 속도",
    "duration_sec_log": "영상 길이 신호",
    "subscriber_count_log": "구독자 규모 신호",
    "upload_hour_sin": "업로드 시간 신호",
    "upload_hour_cos": "업로드 시간 신호",
    "category_id": "영상 카테고리",
    "channel_recent_median_views": "최근 영상 조회수 중앙값",
    "food_keyword_trend_score": "음식 키워드 관심도",
    "season_match_score": "계절 적합도",
    "same_food_upload_count_24h": "최근 24시간 동일 음식 영상 수",
    "weather_food_match_score": "날씨와 음식 주제 적합도",
    "absolute_error": "예측 오차",
    "mean_absolute_error": "평균 예측 오차",
    "mean_absolute_percentage_error": "평균 백분율 예측 오차",
    "evaluated_video_count": "평가 가능한 영상 수",
    "candidate_count": "비교 영상 수",
    "total_video_count": "전체 영상 수",
    "comparison_population": "비교 기준",
    "videos_with_prediction_score": "점수가 있는 영상",
    "videos_with_selected_metric": "해당 비교값이 있는 영상",
    "video_id": "영상 ID",
    "channel_id": "채널 ID",
    "D+3": "게시 후 3일",
    "SHAP": "요소별 영향 분석",
}

# The real context JSON always uses `"key": value` (JSON syntax), never
# `key=value` — but the model paraphrases loosely and can echo either
# separator, with or without quotes, when it leaks a raw field/value pair
# instead of translating it. A plain string entry in INTERNAL_TERM_REPLACEMENTS
# only matches one exact separator, so these need their own flexible regex.
INTERNAL_KEY_VALUE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"['\"]?available['\"]?\s*[:=]\s*['\"]?false['\"]?", re.IGNORECASE),
        "확인할 수 없는 값",
    ),
    (
        re.compile(r"['\"]?available['\"]?\s*[:=]\s*['\"]?true['\"]?", re.IGNORECASE),
        "확인 가능한 값",
    ),
    (
        re.compile(r"['\"]?source['\"]?\s*[:=]\s*['\"]?calculated['\"]?", re.IGNORECASE),
        "직접 계산한 값",
    ),
    (
        re.compile(r"['\"]?source['\"]?\s*[:=]\s*['\"]?stored['\"]?", re.IGNORECASE),
        "저장된 값",
    ),
]

UNSUPPORTED_COHORT_PATTERN = re.compile(
    r"(?:여름|겨울|봄|가을|계절|음식|주제)\s*(?:구간|그룹|군|분류)\s*(?:영상\s*)?중",
    flags=re.IGNORECASE,
)

UNSUPPORTED_INTERPRETATION_REPLACEMENTS = {
    "빠르게 확산 중인 흐름": "조회수가 증가한 상태",
    "빠르게 확산 중": "조회수가 증가 중",
    "폭발적인 성장": "큰 폭의 증가",
    "바이럴 가능성이 상대적으로 높은": "바이럴 점수가 상대적으로 높은",
    "성공 가능성이 높은": "상대 점수가 높은",
    "꾸준히 늘며": "늘어",
    "꾸준히 증가": "증가",
}

# Broader paraphrase patterns for the same unsupported claims. The exact-string
# table above only catches the literal wording; models often say the same thing
# with slightly different conjugation, so these regexes catch common variants
# instead of relying on an ever-growing list of exact phrases.
UNSUPPORTED_INTERPRETATION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"빠르게\s*(?:확산|퍼지|퍼짐|퍼져|번지)[가-힣\s]{0,10}(?:흐름|추세)[가-힣]*",
            re.IGNORECASE,
        ),
        "조회수가 증가한 상태",
    ),
    (
        re.compile(r"폭발적(?:인|으로)?\s*(?:성장|증가|확산)[가-힣]*", re.IGNORECASE),
        "큰 폭의 증가",
    ),
    (
        re.compile(
            r"바이럴\s*(?:가능성|확률)\s*(?:이|가)?\s*상대적으로\s*높[가-힣]*",
            re.IGNORECASE,
        ),
        "바이럴 점수가 상대적으로 높음",
    ),
    (
        re.compile(r"성공\s*(?:가능성|확률)\s*(?:이|가)?\s*높[가-힣]*", re.IGNORECASE),
        "상대 점수가 높음",
    ),
    (
        re.compile(r"꾸준히\s*(?:늘[가-힣]*|증가[가-힣]*|상승[가-힣]*)", re.IGNORECASE),
        "증가",
    ),
]

# metrics.py rounds internal calculations to 4 decimal places for precision,
# but that's noise for a beginner-facing answer (e.g. "0.2709%"). The prompt
# already asks the model to round percentages itself; this is the backstop in
# case it doesn't.
_OVERLY_PRECISE_PERCENT = re.compile(r"(\d+)\.(\d{2,})%")


def _round_percentages(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        value = round(float(f"{match.group(1)}.{match.group(2)}"), 1)
        return f"{value:g}%"

    return _OVERLY_PRECISE_PERCENT.sub(replace, text)


def answer_mode(question: str) -> str:
    """Use a longer answer only when the user explicitly asks for detail."""
    normalized = " ".join(str(question or "").lower().split())
    return (
        "detailed"
        if any(term.lower() in normalized for term in DETAIL_REQUEST_TERMS)
        else "brief"
    )


def answer_schema() -> dict[str, Any]:
    """Return the one strict response shape shared by every question category."""
    return {
        "type": "object",
        "properties": {
            "conclusion": {"type": "string"},
            "key_points": {
                "type": "array",
                "items": {"type": "string"},
            },
            "limitation": {"type": ["string", "null"]},
        },
        "required": ["conclusion", "key_points", "limitation"],
        "additionalProperties": False,
    }


def _is_near_duplicate(candidate: str, reference: str, *, threshold: float = 0.6) -> bool:
    """True if candidate mostly restates reference in different words.

    The exact-string dedup in render_answer only catches literal repeats, but
    the model often re-explains the same fact with slightly different
    wording across conclusion/key_points (e.g. "0~100 범위의 예측값" and
    "0점에서 100점 사이 값" for the same sentence) — this catches that via
    token overlap instead of exact text.
    """
    candidate_tokens = content_tokens(candidate)
    reference_tokens = content_tokens(reference)
    smaller = min(len(candidate_tokens), len(reference_tokens))
    if smaller < 2:
        return False
    overlap = len(candidate_tokens & reference_tokens)
    return (overlap / smaller) >= threshold


def _first_sentence(value: str) -> str:
    parts = re.split(r"(?<=[.!?。])\s+", value, maxsplit=1)
    if len(parts) > 1 and parts[1].strip():
        LOGGER.warning(
            "Dropping extra sentence(s) after the first to keep the one-sentence "
            "contract; original content is not shown to the user: %r",
            parts[1].strip(),
        )
    return parts[0].strip()


def scrub_internal_terms(text: str) -> str:
    """Replace internal field/variable names with the user-facing Korean term.

    Shared by the final answer renderer and the question classifier's
    clarification text, since both are free-form model output that can leak
    raw field names like ``label_score`` if left unscrubbed.
    """
    cleaned = text
    for pattern, friendly_term in INTERNAL_KEY_VALUE_PATTERNS:
        cleaned = pattern.sub(friendly_term, cleaned)
    for internal_term, friendly_term in INTERNAL_TERM_REPLACEMENTS.items():
        cleaned = re.sub(
            rf"(?<![0-9A-Za-z_]){re.escape(internal_term)}(?![0-9A-Za-z_])",
            friendly_term,
            cleaned,
            flags=re.IGNORECASE,
        )
    # "D+3" -> "게시 후 3일" already means "after posting", but the model often
    # also writes "게시 후" right before "D+3" itself (e.g. "게시 후 D+3 시점"),
    # so the substitution above can leave "게시 후 게시 후 3일 시점". Collapse
    # any back-to-back repeat of that phrase down to one.
    cleaned = re.sub(r"(게시\s*후)(?:\s*\1)+", r"\1", cleaned)
    return cleaned


def _clean_text(value: Any, question: str, *, conclusion: bool = False) -> str:
    if not isinstance(value, str):
        return ""
    lines = []
    for line in value.replace("`", "").splitlines():
        cleaned_line = re.sub(r"^\s*(?:#{1,6}\s*|[-*+]\s+|\d+[.)]\s+)", "", line)
        if cleaned_line.strip():
            lines.append(cleaned_line.strip())
    cleaned = " ".join(lines)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if UNSUPPORTED_COHORT_PATTERN.search(cleaned):
        if not conclusion:
            return ""
        cleaned = re.sub(
            r",?\s*[^,.!?]*(?:여름|겨울|봄|가을|계절|음식|주제)\s*"
            r"(?:구간|그룹|군|분류)[^.!?]*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

    for unsupported, neutral in UNSUPPORTED_INTERPRETATION_REPLACEMENTS.items():
        cleaned = re.sub(
            re.escape(unsupported),
            neutral,
            cleaned,
            flags=re.IGNORECASE,
        )
    for pattern, neutral in UNSUPPORTED_INTERPRETATION_PATTERNS:
        cleaned = pattern.sub(neutral, cleaned)

    cleaned = scrub_internal_terms(cleaned)
    cleaned = _round_percentages(cleaned)
    return _first_sentence(cleaned)


def render_answer(
    raw_output: str,
    question: str,
    context_json: str | None = None,
) -> str:
    """Validate structured model output and render a concise plain-text answer."""
    try:
        payload = json.loads(raw_output)
    except (TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("답변 결과가 올바른 JSON 형식이 아닙니다.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("답변 결과가 JSON 객체가 아닙니다.")

    conclusion = _clean_text(payload.get("conclusion"), question, conclusion=True)
    if not conclusion:
        raise RuntimeError("답변 결론이 비어 있습니다.")

    max_points = 6 if answer_mode(question) == "detailed" else 3
    points: list[str] = []
    raw_points = payload.get("key_points")
    if isinstance(raw_points, list):
        for raw_point in raw_points:
            point = _clean_text(raw_point, question)
            already_covered = point and (
                point.casefold() in {
                    conclusion.casefold(),
                    *(item.casefold() for item in points),
                }
                or _is_near_duplicate(point, conclusion)
                or any(_is_near_duplicate(point, item) for item in points)
            )
            if point and not already_covered:
                points.append(point)
            if len(points) >= max_points:
                break

    limitation = _clean_text(payload.get("limitation"), question)
    sections = [conclusion, *points]
    if (
        limitation
        and limitation.casefold() not in {section.casefold() for section in sections}
        and not any(_is_near_duplicate(limitation, section) for section in sections)
    ):
        sections.append(limitation)
    return "\n".join(sections)
