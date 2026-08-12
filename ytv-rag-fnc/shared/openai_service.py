"""Azure OpenAI chat and embedding operations."""

from __future__ import annotations

from functools import lru_cache
import os
from typing import Any

from .answer_policy import answer_mode, answer_schema, render_answer
from .settings import Settings


QUESTION_CATEGORIES = [
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
]

QUESTION_METRICS = [
    "view_count",
    "subscriber_count",
    "like_count",
    "comment_count",
    "engagement_rate",
    "view_velocity",
    "viral_score",
    "label_score",
    "absolute_error",
]


@lru_cache(maxsize=1)
def client() -> Any:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    from openai import OpenAI

    settings = Settings.from_environment()
    if not settings.azure_openai_endpoint:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT 환경 변수가 없습니다.")
    local_api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    credential = local_api_key or get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )
    return OpenAI(
        base_url=f"{settings.azure_openai_endpoint}/openai/v1/",
        api_key=credential,
        timeout=45,
        max_retries=2,
    )


def create_embeddings(texts: list[str]) -> list[list[float]]:
    settings = Settings.from_environment()
    if not settings.embedding_deployment:
        raise RuntimeError("AZURE_OPENAI_EMBEDDING_DEPLOYMENT 환경 변수가 없습니다.")
    cleaned = [str(text).strip() for text in texts]
    if not cleaned or any(not text for text in cleaned):
        raise ValueError("임베딩할 텍스트는 비어 있을 수 없습니다.")
    response = client().embeddings.create(
        model=settings.embedding_deployment,
        input=cleaned,
    )
    ordered = sorted(response.data, key=lambda item: item.index)
    embeddings = [item.embedding for item in ordered]
    if len(embeddings) != len(cleaned):
        raise RuntimeError("Azure OpenAI 임베딩 응답 개수가 요청과 다릅니다.")
    return embeddings


def create_embedding(text: str) -> list[float]:
    return create_embeddings([text])[0]


def create_question_analysis(question: str) -> dict[str, Any]:
    """Classify one question using a strict JSON schema."""
    import json

    settings = Settings.from_environment()
    if not settings.chat_deployment:
        raise RuntimeError("AZURE_OPENAI_CHAT_DEPLOYMENT 환경 변수가 없습니다.")
    schema = {
        "type": "object",
        "properties": {
            "primary_category": {"type": "string", "enum": QUESTION_CATEGORIES},
            "secondary_categories": {
                "type": "array",
                "items": {"type": "string", "enum": QUESTION_CATEGORIES},
            },
            "channel_reference": {"type": ["string", "null"]},
            "video_id": {"type": ["string", "null"]},
            "video_title": {"type": ["string", "null"]},
            "period": {"type": ["string", "null"]},
            "metric": {"type": ["string", "null"], "enum": [*QUESTION_METRICS, None]},
            "needs_clarification": {"type": "boolean"},
            "clarification_question": {"type": ["string", "null"]},
        },
        "required": [
            "primary_category",
            "secondary_categories",
            "channel_reference",
            "video_id",
            "video_title",
            "period",
            "metric",
            "needs_clarification",
            "clarification_question",
        ],
        "additionalProperties": False,
    }
    response = client().responses.create(
        model=settings.chat_deployment,
        # Classification should be reproducible: the same question must land in
        # the same category every time. Without this, repeat calls on
        # identical wording could sample a different category.
        temperature=0,
        instructions=(
            "당신은 YouTube 분석 질문 라우터입니다. 답변을 생성하지 말고 질문을 구조화하세요. "
            "카테고리 정의: channel_growth=채널 전체 현황·성장, video_list=현재 채널 영상 목록, "
            "video_performance=개별 영상 성과, "
            "prediction_score=영상 예측 점수, shap_factors=점수에 영향을 준 피처·SHAP 요인, "
            "prediction_vs_actual=예측과 실제 비교, video_ranking=영상 비교·Top N·순위, "
            "model_evaluation=채널 영상 전체에서 모델 예측 정확도·평균 오차 평가, "
            "channel_baseline_comparison=해당 채널의 평소 영상과 비교, data_status=수집·예측·라벨 누락 상태, "
            "glossary_model=용어·피처·모델 설명. 복합 질문은 가장 중요한 의도를 primary로 두고 나머지를 secondary에 넣으세요. "
            "channel_reference는 질문에 특정 채널명이나 channel_id가 명시된 경우에만 기록하고 "
            "'내 채널', '우리 채널', '현재 채널'이면 null로 두세요. "
            "video_id와 video_title도 질문에 명시된 내용만 기록하세요. "
            "channel_growth 질문은 기간이나 지표가 생략되어도 needs_clarification=false로 두세요. "
            "이 경우 서비스가 보유한 전체 스냅샷 기간과 구독자·조회수 지표를 기본으로 사용합니다. "
            "video_list, video_ranking, model_evaluation, data_status, glossary_model도 세부 지표가 없어도 기본값으로 답할 수 있으므로 되묻지 마세요. "
            "'이 영상'처럼 대상이 불명확해 답변할 수 없으면 needs_clarification=true로 하고 한국어 확인 질문을 작성하세요. "
            "clarification_question에는 label_score, viral_score 같은 내부 필드명, 변수명, 코드 용어를 절대 쓰지 말고 "
            "'실제 성과 점수', '바이럴 점수'처럼 사용자가 이해하는 쉬운 한국어 표현만 쓰세요. "
            "metric은 허용된 표준 이름 중 가장 핵심인 하나만 선택하세요."
        ),
        input=question,
        text={
            "format": {
                "type": "json_schema",
                "name": "youtube_question_analysis",
                "description": "YouTube RAG routing category and explicitly mentioned entities",
                "strict": True,
                "schema": schema,
            }
        },
    )
    output = (response.output_text or "").strip()
    if not output:
        raise RuntimeError("Azure OpenAI가 질문 분류 결과를 반환하지 않았습니다.")
    parsed = json.loads(output)
    if not isinstance(parsed, dict):
        raise RuntimeError("Azure OpenAI 질문 분류 결과가 객체가 아닙니다.")
    return parsed


def create_answer(question: str, context_json: str) -> str:
    settings = Settings.from_environment()
    if not settings.chat_deployment:
        raise RuntimeError("AZURE_OPENAI_CHAT_DEPLOYMENT 환경 변수가 없습니다.")
    mode = answer_mode(question)
    mode_instruction = (
        "사용자가 상세 설명을 요청했습니다. 핵심 근거를 최대 6개까지 사용할 수 있습니다."
        if mode == "detailed"
        else "기본 답변입니다. 결론과 질문에 직접 필요한 핵심 근거만 사용하고 핵심 근거는 최대 3개로 제한하세요."
    )
    response = client().responses.create(
        model=settings.chat_deployment,
        # Low temperature for the same reason as the classifier: grounded,
        # numeric answers should stay consistent across repeat calls rather
        # than vary with sampling (this is also what let the earlier "만/억"
        # unit-conversion arithmetic slip through inconsistently).
        temperature=0,
        instructions=(
            "당신은 YouTube Viral Radar의 데이터 해석 도우미입니다. "
            "모든 질문에 같은 전역 답변 규칙을 적용하세요. 카테고리별 문구나 고정 템플릿을 사용하지 마세요. "
            "제공된 근거에 있는 사실만 사용하고 비전문가가 이해하기 쉬운 한국어로 답하세요. "
            "conclusion에는 질문의 직접 답변만 한 문장으로 쓰세요. "
            "key_points에는 결론을 이해하는 데 직접 필요한 수치나 사실만 각각 한 문장으로 쓰고, 결론을 반복하지 마세요. "
            "conclusion에서 이미 말한 정의·범위·조건(예: 점수 범위가 0~100이라는 것, 성공 확률이 아니라는 것)을 "
            "key_points에서 표현만 바꿔 다시 설명하지 마세요. key_points 각 문장은 서로도 겹치지 않는 별개의 새 정보여야 하며, "
            "새로 추가할 정보가 없으면 key_points를 비워두세요. "
            "limitation은 결론의 정확도나 해석에 실제로 영향을 주는 데이터 부족이 있을 때만 한 문장으로 쓰며, 없으면 null로 두세요. "
            "질문과 관계없는 데이터 보유율, 시스템 상태, 데이터 출처를 덧붙이지 마세요. "
            "제공된 근거에 없는 수치, 영상, 채널 정보는 절대로 만들지 마세요. "
            "숫자를 '만', '억' 같은 단위로 직접 환산하지 마세요. 제공된 원본 숫자에 천 단위 콤마만 넣어 "
            "그대로 표기하세요 (예: 13400000은 '1,340만'이 아니라 '13,400,000'으로 표기). "
            "단위 환산은 계산 실수가 나기 쉬우니 원본 자릿수를 절대 바꾸지 마세요. "
            "백분율(%) 수치는 초보자가 읽기 쉽도록 소수점 첫째 자리까지만 반올림해서 쓰세요 "
            "(예: 0.2709%는 0.3%로). "
            "비교 기준 수치가 없으면 '빠르다', '높은 편', '상위권', '잘됐다'처럼 상대 평가하지 마세요. "
            "영상 제목, 음식명, 계절 키워드를 이용해 '여름 영상군' 같은 비교 집단을 새로 만들지 마세요. "
            "증가 전후 값만 있으면 '증가했다'고만 말하고, 시점이 여러 개 있어도 추세 검증 없이 '꾸준히'라고 표현하지 마세요. "
            "순위를 말할 때는 실제 비교값이 있는 영상 수를 기준으로 하고 전체 영상 수와 혼동하지 마세요. "
            "내부 JSON 경로, 변수명, 테이블명, source 값, CONTEXT 같은 시스템 용어를 사용자에게 노출하지 마세요. "
            "video_id 문자열(예: 11자리 영문/숫자 코드)을 답변에 직접 쓰지 마세요. 특정 영상을 가리켜야 하면 "
            "영상 제목이나 '선택한 영상'이라고 표현하세요. "
            "데이터 항목 이름은 사용자가 질문에 직접 썼더라도 답변에서 반복하지 말고 반드시 쉬운 의미로 바꾸세요. "
            "예를 들어 viral_score는 '바이럴 점수', views_6h_log는 '게시 후 6시간 조회수 신호', "
            "engagement_rate는 '참여율', duration_sec_log는 '영상 길이 신호'라고 표현하세요. "
            "마크다운 제목, 글머리표, 코드 표시는 각 필드에 넣지 마세요. "
            f"{mode_instruction} "
            "바이럴 점수는 성공 확률이 아니라 후보 집합 안의 상대 점수로 설명하세요. "
            "30분 간격 스냅샷, D+3 label_score, 레거시 7일 예측값을 서로 구분하세요. "
            "local_explanation.method가 synthetic_shap_like이면 실제 SHAP라고 부르지 말고 "
            "'설명용 합성 피처 영향도'라고 표현하세요. "
            "피처 영향은 모델의 연관 신호이며 실제 인과관계라고 단정하지 마세요. "
            "값이 없거나 사용할 수 없다고 표시된 항목은 추측하지 마세요. "
            "용어 설명 자료는 실제 채널 수치가 아니며 검색 관련도도 모델 예측 점수가 아닙니다. "
            "다른 채널을 추측하거나 언급하지 마세요."
        ),
        input=f"제공된 근거\n{context_json}\n\n사용자 질문\n{question}",
        text={
            "format": {
                "type": "json_schema",
                "name": "youtube_rag_answer",
                "description": "A concise, grounded Korean answer for a YouTube analytics question",
                "strict": True,
                "schema": answer_schema(),
            }
        },
    )
    output = (response.output_text or "").strip()
    if not output:
        raise RuntimeError("Azure OpenAI가 빈 응답을 반환했습니다.")
    return render_answer(output, question, context_json)
