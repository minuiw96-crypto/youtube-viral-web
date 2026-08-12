"""Classify a free-form question and extract safe RAG routing entities."""

from __future__ import annotations

import logging
import re
from typing import Any

from .answer_policy import scrub_internal_terms
from .openai_service import create_question_analysis


LOGGER = logging.getLogger(__name__)

CATEGORIES = (
    "channel_growth",
    "video_list",
    "video_performance",
    "prediction_score",
    "shap_factors",
    "prediction_vs_actual",
    "model_evaluation",
    "video_ranking",
    "channel_baseline_comparison",
    "data_status",
    "glossary_model",
)

METRICS = (
    "view_count",
    "subscriber_count",
    "like_count",
    "comment_count",
    "engagement_rate",
    "view_velocity",
    "viral_score",
    "label_score",
    "absolute_error",
)

DEFAULT_CLARIFICATION = "분석할 영상이나 기간을 조금 더 구체적으로 알려주세요."

# Words that can legitimately sit right before "채널" without naming a specific
# channel (determiners, temporal/quantity adverbs). Shared with rag_service.py's
# enforce_question_scope so both layers agree on what counts as a real channel name.
GENERIC_CHANNEL_QUALIFIERS = {
    "내", "나", "저", "제", "우리", "저희", "현재", "지금", "이번",
    "해당", "이", "그", "요즘", "최근", "최신", "전체", "모든", "본",
    "오늘", "어제", "유튜브", "youtube",
}
_PERIOD_TOKEN_PATTERN = re.compile(r"^\d+(?:년|개월|달|주|일|시간|분|초)$")


def _is_generic_channel_word(value: str) -> bool:
    normalized = value.strip().casefold()
    if not normalized:
        return True
    return normalized in GENERIC_CHANNEL_QUALIFIERS or bool(
        _PERIOD_TOKEN_PATTERN.match(normalized)
    )

# These categories can answer from the data already available for the signed-in
# channel. Missing period/metric is not a reason to interrupt the user.
CHANNEL_DEFAULT_CATEGORIES = {
    "channel_growth",
    "video_list",
    "video_ranking",
    "data_status",
    "model_evaluation",
    "glossary_model",
}


def _deterministic_primary_category(question: str) -> str | None:
    """Return a high-confidence intent that should not depend on model wording."""
    compact = re.sub(r"\s+", "", question.lower())

    glossary_markers = ("뜻", "뭐야", "무엇", "차이", "설명", "정의", "의미")
    glossary_terms = (
        "shap",
        "피처",
        "feature",
        "views_1h_log",
        "views_6h_log",
        "view_velocity",
        "조회증가속도",
        "조회속도",
        "시간당조회",
        "참여율",
        "바이럴점수",
        "모델",
        "xgboost",
        "라벨",
        "d+3",
    )
    if any(marker in compact for marker in glossary_markers) and any(
        term in compact for term in glossary_terms
    ):
        return "glossary_model"

    # "바이럴 점수는 어떻게 계산되나요?" / "몇 점부터 높은 점수인가요?" / "예측 점수와
    # 실제 성과는 어떻게 다른가요?" all ask about the scoring concept itself, not
    # one video's number. They rarely contain "바이럴점수" as one glued token or
    # any glossary_markers word above, so the rule right above misses them and
    # they fall through to a video-required category — and since nothing here
    # forces a specific classification, repeat calls can land differently.
    no_video_pronoun = not any(
        marker in compact for marker in ("이영상", "그영상", "해당영상")
    )
    if (
        any(term in compact for term in ("점수", "참여율", "성장률"))
        and any(
            word in compact
            for word in ("계산되나요", "계산돼요", "계산되는", "계산방식", "계산식", "산출되나요", "산출방식")
        )
        and no_video_pronoun
    ):
        return "glossary_model"
    if (
        "점수" in compact
        and any(marker in compact for marker in ("뜻인가요", "뜻이야", "무슨뜻", "의미인가요"))
        and no_video_pronoun
    ):
        return "glossary_model"
    if any(word in compact for word in ("몇점부터", "몇점이상", "최고점", "최저점", "만점")) and no_video_pronoun:
        return "glossary_model"
    if (
        "예측" in compact
        and any(term in compact for term in ("실제성과", "실제점수", "실제와", "라벨"))
        and any(marker in compact for marker in ("다른가요", "다른지", "차이"))
        and no_video_pronoun
    ):
        return "glossary_model"

    # "쇼츠 영상도 분석할 수 있나요?" / "유튜브 URL만 입력하면 분석되나요?" ask
    # whether the product supports a whole class of input, not to analyze one
    # selected video. Without this, they fall into a video-required category
    # and either demand a video id or answer with unrelated data-coverage
    # stats. Exclude questions that name a specific video, since those really
    # do want that video's own analysis.
    capability_phrases = (
        "분석할수있나요", "분석할수있어요", "분석가능한가요", "분석가능해요", "분석되나요",
        "예측할수있나요", "예측할수있어요", "예측가능한가요", "예측가능해요", "예측되나요",
    )
    has_specific_video = any(
        marker in compact for marker in ("이영상", "그영상", "해당영상")
    ) or bool(re.search(r"youtu\.be/|[?&]v=", question, flags=re.IGNORECASE))
    if any(phrase in compact for phrase in capability_phrases) and not has_specific_video:
        return "glossary_model"

    # "영상 분석에는 얼마나 걸리나요?" asks about product turnaround time, not a
    # specific video's own timeline — same class of question as the
    # capability_phrases above, just phrased as a duration instead of a
    # yes/no possibility.
    if (
        any(term in compact for term in ("분석", "예측"))
        and any(word in compact for word in ("얼마나걸리나요", "얼마나걸려요", "소요시간", "얼마나걸리는지"))
        and not has_specific_video
    ):
        return "glossary_model"

    # "같은 카테고리 평균 점수는 몇 점인가요?" asks for an aggregate across many
    # videos, not one video's score — "몇점" further below would otherwise
    # route this into prediction_score, which requires a selected video.
    if any(term in compact for term in ("카테고리평균", "카테고리별평균", "전체평균")) and "점수" in compact:
        return "video_ranking"

    # "PredictTube는 정확히 어떤 서비스인가요?" asks what the product itself is,
    # not for channel/video data.
    if any(
        term in compact for term in ("predicttube", "프리딕트튜브", "이서비스", "이앱")
    ) and any(marker in compact for marker in ("무엇", "뭐야", "뭔가요", "어떤서비스", "설명")):
        return "glossary_model"

    # "실험실에 있는 저건 뭐야?" asks what a product screen/feature is, not for
    # channel/video data.
    if any(
        term in compact for term in ("실험실", "영상인사이트", "lab")
    ) and any(marker in compact for marker in ("뭐야", "무엇", "뭔가요", "설명")):
        return "glossary_model"

    video_list_patterns = (
        "영상목록",
        "영상리스트",
        "영상뭐뭐",
        "영상이뭐",
        "어떤영상",
        "영상들보여",
        "영상보여줘",
        "소유하고있는영상",
        "업로드한영상",
        "올린영상",
    )
    if any(pattern in compact for pattern in video_list_patterns):
        return "video_list"

    if any(
        pattern in compact
        for pattern in (
            "데이터충족률",
            "예측데이터충족률",
            "라벨데이터충족률",
            "스냅샷충족률",
            "데이터커버리지",
            "예측커버리지",
            "몇퍼센트수집",
        )
    ):
        return "data_status"

    if (
        any(word in compact for word in ("모델", "예측"))
        and any(word in compact for word in ("정확", "정확도", "얼마나맞", "전체오차"))
        and "영상" not in compact
    ):
        return "model_evaluation"

    if (
        any(word in compact for word in ("빗나간", "틀린", "오차", "차이"))
        and any(word in compact for word in ("가장", "제일", "순위", "랭킹"))
        and any(word in compact for word in ("예측", "모델", "실제"))
    ):
        return "video_ranking"

    # "이 영상의 점수는 어떻게 나온거야?" is asking what drove one video's score —
    # real users rarely say "SHAP" or "피처" outright, so without this the
    # model has to guess between a thin "just the number" answer
    # (prediction_score) and the richer factor breakdown (shap_factors).
    # Route it deterministically so the explanation always comes through.
    if (
        any(marker in compact for marker in ("이영상", "그영상", "해당영상"))
        and "점수" in compact
        and any(word in compact for word in ("어떻게", "왜", "이유", "원인"))
    ):
        return "shap_factors"

    # "이 영상이 상위권이야?" is asking whether one specific video beats the
    # channel's own baseline, not for a channel-wide ranking list. Without this
    # check, the "상위" keyword below would route it to video_ranking, which
    # skips clarification and drops the "이 영상" reference entirely.
    if any(
        marker in compact for marker in ("이영상", "그영상", "해당영상")
    ) and any(
        word in compact
        for word in ("top", "순위", "랭킹", "상위", "높", "좋은편", "잘된", "괜찮")
    ):
        return "channel_baseline_comparison"

    if any(
        word in compact
        for word in ("top", "순위", "랭킹", "상위", "가장좋", "제일좋", "최고영상", "추천", "유망")
    ):
        return "video_ranking"

    # "최근 점수가 높은 영상들의 공통점?" asks about a pattern across several
    # videos, not one — "top/순위/상위" above don't catch "높은" on its own, but
    # "공통점/패턴/특징" combined with "영상" and a performance word is an
    # unambiguous cross-video signal that belongs in the ranking/comparison flow.
    if (
        any(word in compact for word in ("공통점", "공통된", "패턴", "특징"))
        and "영상" in compact
        and any(word in compact for word in ("점수", "성과", "잘된", "상위", "높은", "조회수"))
    ):
        return "video_ranking"

    # "나와 비슷한 채널 중에서 나는 어느정도야?" is asking to be ranked against
    # other channels, which the answer policy already forbids discussing. Route
    # it to channel_growth (video-free, always answerable) so the model can
    # honestly say it has no other channel's data, instead of silently
    # substituting this channel's own videos for the "other channel" the
    # question actually asked about. Only skip this when a specific video is
    # named ("이 영상"/"그 영상"/"해당 영상") — "다른 채널의 영상들은 어때?" still
    # has to be excluded here even though it contains "영상", since that's a
    # generic plural reference, not a single video to look up.
    if any(
        word in compact
        for word in ("비슷한채널", "다른채널", "타채널", "유사채널", "동종채널")
    ) and not any(
        marker in compact for marker in ("이영상", "그영상", "해당영상")
    ):
        return "channel_growth"

    channel_scope = any(word in compact for word in ("채널", "우리", "내", "전체"))
    channel_summary = any(
        word in compact
        for word in (
            "성과",
            "성장세",
            "성장",
            "현황",
            "구독자",
            "총조회수",
            "누적조회수",
            "채널규모",
            "처음수집",
            "수집했을때",
            "처음과지금",
        )
    )
    # "구독자" is a channel-only metric (no single video has a subscriber count),
    # so it implies channel scope even without an explicit "채널/우리" word —
    # e.g. "구독자는 늘었는데 조회수도 같이 늘고 있어?" names no channel keyword.
    if (channel_scope or "구독자" in compact) and channel_summary and "영상" not in compact:
        return "channel_growth"
    return None


def apply_deterministic_routing(
    question: str,
    analysis: dict[str, Any],
) -> dict[str, Any]:
    """Override only broad, high-confidence intents shared by all backends."""
    primary = _deterministic_primary_category(question)
    if not primary:
        return analysis
    result = dict(analysis)
    result["primary_category"] = primary
    result["secondary_categories"] = []
    compact = re.sub(r"\s+", "", question.lower())
    if primary == "video_ranking" and any(
        word in compact for word in ("빗나간", "틀린", "오차")
    ):
        result["metric"] = "absolute_error"
    if primary in CHANNEL_DEFAULT_CATEGORIES:
        result["needs_clarification"] = False
        result["clarification_question"] = None
    return result


def _clean_optional(value: Any, max_length: int = 200) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned[:max_length] if cleaned else None


def normalize_question_analysis(raw: Any, source: str = "azure_openai") -> dict[str, Any]:
    """Validate the model result and return the stable internal contract."""
    data = raw if isinstance(raw, dict) else {}
    primary = str(data.get("primary_category") or "").strip()
    if primary not in CATEGORIES:
        primary = "video_performance"

    secondary = []
    for item in data.get("secondary_categories") or []:
        value = str(item or "").strip()
        if value in CATEGORIES and value != primary and value not in secondary:
            secondary.append(value)

    metric = _clean_optional(data.get("metric"), 50)
    if metric not in METRICS:
        metric = None

    needs_clarification = data.get("needs_clarification") is True
    clarification = _clean_optional(data.get("clarification_question"), 300)
    if clarification:
        clarification = scrub_internal_terms(clarification)
    if primary in CHANNEL_DEFAULT_CATEGORIES:
        needs_clarification = False
        clarification = None
    if needs_clarification and not clarification:
        clarification = DEFAULT_CLARIFICATION

    return {
        "primary_category": primary,
        "secondary_categories": secondary,
        "channel_reference": _clean_optional(data.get("channel_reference")),
        "video_id": _clean_optional(data.get("video_id"), 100),
        "video_title": _clean_optional(data.get("video_title")),
        "period": _clean_optional(data.get("period"), 100),
        "metric": metric,
        "needs_clarification": needs_clarification,
        "clarification_question": clarification,
        "source": source,
    }


def _fallback_category(question: str) -> tuple[str, list[str]]:
    compact = re.sub(r"\s+", "", question.lower())
    categories = []

    deterministic = _deterministic_primary_category(question)
    if deterministic:
        return deterministic, []

    if any(word in compact for word in ("왜없", "아직", "누락", "수집안", "데이터상태")):
        categories.append("data_status")
    if (
        any(word in compact for word in ("모델", "예측"))
        and any(word in compact for word in ("정확", "얼마나맞", "전체오차"))
        and "영상" not in compact
    ):
        categories.append("model_evaluation")
    if ("예측" in compact and any(word in compact for word in ("실제", "맞았", "오차", "결과"))):
        categories.append("prediction_vs_actual")
    if any(word in compact for word in ("shap", "피처영향", "영향요인", "점수가왜", "왜점수")):
        categories.append("shap_factors")
    if any(word in compact for word in ("top", "순위", "랭킹", "추천", "상위")):
        categories.append("video_ranking")
    if any(word in compact for word in ("평소", "평균보다", "보통영상", "채널기준", "중앙값")):
        categories.append("channel_baseline_comparison")
    if any(word in compact for word in ("몇점", "예측점수", "바이럴점수")):
        categories.append("prediction_score")
    if any(word in compact for word in ("성장세", "채널성장", "구독자증가", "채널현황")):
        categories.append("channel_growth")
    if any(word in compact for word in ("조회수", "좋아요", "댓글", "참여율", "반응", "성과")):
        categories.append("video_performance")
    if any(word in compact for word in ("뜻", "뭐야", "정의", "설명해")) and any(
        word in compact for word in ("shap", "피처", "참여율", "바이럴점수", "모델", "xgboost", "라벨")
    ):
        categories.append("glossary_model")

    if not categories:
        categories.append("video_performance")
    return categories[0], categories[1:]


def _fallback_period(question: str) -> str | None:
    patterns = (
        r"D\s*\+\s*\d+",
        r"최근\s*\d+\s*(?:시간|일|주|개월)",
        r"(?:업로드\s*후\s*)?\d+\s*(?:분|시간|일)",
    )
    for pattern in patterns:
        match = re.search(pattern, question, flags=re.IGNORECASE)
        if match:
            return re.sub(r"\s+", "", match.group(0))
    return None


def _fallback_metric(question: str) -> str | None:
    aliases = (
        ("구독자", "subscriber_count"),
        ("조회 증가", "view_velocity"),
        ("조회속도", "view_velocity"),
        ("조회수", "view_count"),
        ("좋아요", "like_count"),
        ("댓글", "comment_count"),
        ("참여율", "engagement_rate"),
        ("바이럴 점수", "viral_score"),
        ("바이럴점수", "viral_score"),
        ("실제 성과", "label_score"),
        ("실제 점수", "label_score"),
        ("실제점수", "label_score"),
        ("빗나간", "absolute_error"),
        ("예측 오차", "absolute_error"),
        ("예측오차", "absolute_error"),
    )
    compact = question.lower()
    for alias, metric in aliases:
        if alias in compact:
            return metric
    return None


def _fallback_channel_reference(question: str) -> str | None:
    channel_id = re.search(r"\bUC[0-9A-Za-z_-]{6,}\b", question)
    if channel_id:
        return channel_id.group(0)

    # Capture only the single word immediately before each "채널" occurrence
    # (not an unbounded run back to the start of the sentence) so a sentence
    # like "최근 채널 성장세" or "지금 채널 규모" doesn't get misread as a
    # specific channel name. Scan every occurrence, since a question can
    # mention the user's own channel generically before naming another one
    # explicitly later (e.g. "우리 채널이랑 다른 채널을 비교해줘").
    for match in re.finditer(r"(\S+)\s*채널", question):
        value = match.group(1).strip()
        if not _is_generic_channel_word(value):
            return value
    return None


def lexical_question_analysis(
    question: str,
    *,
    source: str = "lexical_fallback",
) -> dict[str, Any]:
    """Low-cost deterministic fallback used when classification is unavailable."""
    primary, secondary = _fallback_category(question)
    youtube_url = re.search(r"(?:youtu\.be/|[?&]v=)([0-9A-Za-z_-]{6,})", question)
    return apply_deterministic_routing(
        question,
        normalize_question_analysis(
            {
                "primary_category": primary,
                "secondary_categories": secondary,
                "channel_reference": _fallback_channel_reference(question),
                "video_id": youtube_url.group(1) if youtube_url else None,
                "video_title": None,
                "period": _fallback_period(question),
                "metric": _fallback_metric(question),
                "needs_clarification": False,
                "clarification_question": None,
            },
            source=source,
        ),
    )


def analyze_question(question: str) -> dict[str, Any]:
    """Use Azure OpenAI structured output, falling back without breaking chat."""
    if _deterministic_primary_category(question):
        return lexical_question_analysis(question, source="deterministic_rules")
    try:
        analysis = normalize_question_analysis(create_question_analysis(question))
    except Exception:
        LOGGER.exception("Question classification failed; using lexical fallback.")
        analysis = lexical_question_analysis(question)
    return apply_deterministic_routing(question, analysis)
