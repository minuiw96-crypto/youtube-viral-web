"""Versioned feature and metric explanations used by embedding search."""

from __future__ import annotations

from typing import Any

from .search_normalization import lexical_rank_documents


KNOWLEDGE_VERSION = "2.4.0"


KNOWLEDGE_DOCUMENTS: list[dict[str, Any]] = [
    {
        "id": "concept-viral-score",
        "title": "바이럴 점수",
        "aliases": [
            "viral_score", "예측 점수", "바이럴 예측", "최고점", "최저점", "점수 범위",
            "계산 방식", "시그모이드", "IQR 보정", "산출 방식", "몇 점부터 높은 점수",
        ],
        "topic": "prediction",
        "content": (
            "바이럴 점수는 후보 영상 집합 안에서 모델이 예상한 상대적인 성과 점수다. "
            "0점에서 100점 사이의 값으로 표현되며, 성공 확률이나 확정 조회수가 아니다. "
            "같은 후보군과 같은 모델 버전 안에서 비교해야 한다. 계산 방식은 게시 후 3일(D+3) 시점 "
            "조회수를 채널·카테고리의 평소 기대 성과와 비교한 상대 성과로 만든 뒤, 로그 변환과 "
            "IQR(사분위) 보정을 거쳐 시그모이드 함수로 0~100점에 매핑하는 것이다. 대략 50점은 평소 "
            "기대한 수준과 비슷한 성과를, 75점 근처는 기대를 크게 초과한 상위권 성과를 의미한다. "
            "원본 조회수를 그대로 쓰지 않고 상대 성과로 변환하는 이유는 채널 규모나 특정 영상의 "
            "극단치가 점수를 왜곡하지 않게 하기 위해서다."
        ),
    },
    {
        "id": "concept-channel-personalization",
        "title": "채널별 개인화(Channel Weight)",
        "aliases": ["개인화", "채널 가중치", "새 채널 예측", "그룹 기준", "채널 기준"],
        "topic": "prediction",
        "content": (
            "바이럴 점수의 기준선은 데이터가 적은 채널일수록 카테고리 전체(Group Baseline)에 더 "
            "의존하고, 그 채널의 실제 게시 후 3일 성과 데이터가 쌓일수록 그 채널 자체(Channel "
            "Baseline)의 비중이 커지는 방식으로 자동 조정된다. 그래서 신규 채널은 카테고리 평균에 "
            "가까운 기준으로, 데이터가 많은 채널은 그 채널만의 평소 성과를 기준으로 점수가 매겨진다."
        ),
    },
    {
        "id": "product-data-protection-and-ai-ethics",
        "title": "데이터 보호와 AI 윤리 원칙",
        "aliases": ["데이터 보호", "개인정보", "AI 윤리", "데이터는 어떻게 저장", "안전한가요"],
        "topic": "product_faq",
        "content": (
            "입력한 영상·채널 정보가 모델 학습에 사용될 수 있다는 점을 사용자에게 명시하며, 메타 "
            "정보는 사용 후 삭제하는 것을 원칙으로 한다. 부적절한 데이터 유입을 막는 검증 로직을 "
            "적용하고 있다. 예측값은 확정된 사실이 아닌 예측성 수치임을 사용자 인터페이스에 명시해 "
            "신뢰성을 관리한다."
        ),
    },
    {
        "id": "product-differentiation",
        "title": "다른 서비스와의 차이점",
        "aliases": ["다른 서비스", "경쟁 서비스", "차별점", "ViewStats", "VidIQ"],
        "topic": "product_faq",
        "content": (
            "다른 유튜브 분석 서비스들은 주로 '무엇을 찍어야 뜨는지'를 추천하는 데 초점을 맞춘다. "
            "이 서비스는 반대로 이미 만든(또는 게시 전) 영상이 뜰지 안 뜰지를 게시 시점 정보만으로 "
            "예측해 답하는 데 초점을 맞춘다."
        ),
    },
    {
        "id": "concept-label-score",
        "title": "실제 점수와 D+3 라벨",
        "aliases": ["label_score", "actual score", "실제 성과", "D+3"],
        "topic": "evaluation",
        "content": (
            "label_score는 게시 후 D+3 시점의 관측값으로 계산한 실제 성과 라벨이다. "
            "predicted_score 또는 viral_score와 비교해 모델의 과대·과소 예측과 오차를 평가한다."
        ),
    },
    {
        "id": "concept-shap",
        "title": "SHAP과 영상별 설명",
        "aliases": ["SHAP", "feature impact", "local explanation", "점수 반영 요소"],
        "topic": "explainability",
        "content": (
            "SHAP은 한 영상의 예측에서 각 입력 피처가 기준 예측보다 점수를 얼마나 올리거나 내렸는지 "
            "설명하는 방법이다. 양수는 점수 상승 방향, 음수는 하락 방향을 뜻하지만 인과관계를 증명하지는 않는다. "
            "local_explanation.method가 synthetic_shap_like이면 실제 SHAP이 아니라 설명용 근사치로 구분해야 한다."
        ),
    },
    {
        "id": "concept-feature-importance",
        "title": "전역 피처 중요도와 영상별 SHAP의 차이",
        "aliases": ["feature importance", "피처 중요도", "global importance"],
        "topic": "explainability",
        "content": (
            "전역 피처 중요도는 전체 모델에서 어떤 피처가 자주 중요했는지를 보여준다. "
            "영상별 SHAP은 선택한 영상 하나에서 각 피처가 어떤 방향으로 작용했는지를 보여준다. "
            "전역 중요도로 개별 영상의 점수 원인을 단정하면 안 된다."
        ),
    },
    {
        "id": "concept-prediction-error",
        "title": "예측값과 실제값의 오차",
        "aliases": ["absolute_error", "prediction error", "과대 예측", "과소 예측"],
        "topic": "evaluation",
        "content": (
            "오차는 실제 점수에서 예측 점수를 뺀 값이다. 실제값이 더 크면 과소 예측, 예측값이 더 크면 "
            "과대 예측이다. 절대오차는 방향을 제거한 오차 크기이며, 실제값이 0이면 백분율 오차는 계산하지 않는다."
        ),
    },
    {
        "id": "concept-time-horizons",
        "title": "30분 스냅샷과 D+3 평가 시점",
        "aliases": ["snapshot", "30분", "72시간", "D+3", "time horizon"],
        "topic": "data_collection",
        "content": (
            "video_snapshots는 영상 게시 후의 조회수·좋아요·댓글을 반복 수집한 기록이다. "
            "프로젝트 계획상 게시 후 D+30까지 30분 간격으로 추적할 수 있고, 모델 평가는 D+3 라벨을 사용한다. "
            "질문의 기간과 실제 저장된 snapshot_time을 확인해 같은 시점을 비교해야 한다."
        ),
    },
    {
        "id": "metric-engagement-rate",
        "title": "참여율",
        "aliases": ["engagement_rate", "반응률", "좋아요 댓글 비율"],
        "topic": "metric",
        "content": (
            "현재 RAG 계산식의 참여율은 (좋아요 수 + 댓글 수) / 조회수 × 100이다. "
            "조회수가 없거나 0이면 계산하지 않는다. 프로젝트의 최종 정의가 바뀌면 계산식 버전도 함께 변경해야 한다."
        ),
    },
    {
        "id": "metric-view-velocity",
        "title": "조회 증가 속도",
        "aliases": ["view_velocity", "조회수 속도", "시간당 조회수"],
        "topic": "metric",
        "content": (
            "조회 증가 속도는 두 스냅샷 사이의 조회수 증가량을 경과 시간으로 나눈 시간당 조회수다. "
            "최소 두 개의 정상적인 시간 스냅샷이 필요하며, 단일 스냅샷만 있으면 계산할 수 없다."
        ),
    },
    {
        "id": "metric-growth-rate",
        "title": "채널 성장률",
        "aliases": ["growth_rate", "구독자 성장률", "조회수 성장률"],
        "topic": "metric",
        "content": (
            "성장률은 (현재값 - 이전값) / 이전값 × 100이다. channel_snapshots의 서로 다른 두 시점을 사용하며, "
            "이전값이 0이거나 값이 누락되면 계산하지 않는다."
        ),
    },
    {
        "id": "metric-data-coverage",
        "title": "데이터 충족률",
        "aliases": ["coverage", "데이터 누락", "예측 없음", "라벨 없음"],
        "topic": "data_quality",
        "content": (
            "데이터 충족률은 채널의 전체 영상 중 예측·라벨·스냅샷이 존재하는 영상의 비율이다. "
            "한 영상에 문서가 여러 개 있어도 영상 한 건으로 계산해야 한다."
        ),
    },
    {
        "id": "feature-subscriber-count-log",
        "title": "subscriber_count_log",
        "aliases": ["subscriber_count", "구독자 수 로그", "채널 규모"],
        "topic": "model_feature",
        "content": (
            "subscriber_count_log는 채널 구독자 수에 로그 변환을 적용한 피처다. "
            "채널 규모의 큰 수치 차이를 완화해 모델이 사용하기 쉽게 만든 값이며 원래 구독자 수 그 자체가 아니다."
        ),
    },
    {
        "id": "feature-views-1h-log",
        "title": "views_1h_log",
        "aliases": ["1시간 조회수", "초기 조회수", "views 1h"],
        "topic": "model_feature",
        "content": (
            "views_1h_log는 게시 후 약 1시간 시점의 조회수에 로그 변환을 적용한 피처다. "
            "영상의 매우 초기 반응을 나타내며 정확한 계산 기준 시점은 팀의 전처리 정의를 따라야 한다."
        ),
    },
    {
        "id": "feature-views-6h-log",
        "title": "views_6h_log",
        "aliases": ["6시간 조회수", "초기 성장", "views 6h"],
        "topic": "model_feature",
        "content": (
            "views_6h_log는 게시 후 약 6시간 시점의 조회수에 로그 변환을 적용한 피처다. "
            "1시간 피처보다 조금 더 누적된 초기 성장세를 모델에 전달한다."
        ),
    },
    {
        "id": "feature-duration-sec-log",
        "title": "duration_sec_log",
        "aliases": ["영상 길이", "duration", "재생 시간"],
        "topic": "model_feature",
        "content": (
            "duration_sec_log는 영상 길이(초)에 로그 변환을 적용한 피처다. "
            "길이가 매우 긴 영상의 수치 영향을 완화하며, 길이가 성과의 직접 원인이라는 뜻은 아니다."
        ),
    },
    {
        "id": "feature-upload-time",
        "title": "upload_hour_sin과 upload_hour_cos",
        "aliases": ["업로드 시간", "upload_hour_sin", "upload_hour_cos", "게시 시간"],
        "topic": "model_feature",
        "content": (
            "upload_hour_sin과 upload_hour_cos는 0시와 23시가 서로 가깝다는 시간의 순환성을 보존하기 위해 "
            "업로드 시각을 사인과 코사인 두 값으로 변환한 피처다. 두 값을 함께 해석해야 한다."
        ),
    },
    {
        "id": "feature-category-id",
        "title": "category_id",
        "aliases": ["카테고리", "영상 분류", "YouTube category"],
        "topic": "model_feature",
        "content": (
            "category_id는 영상의 콘텐츠 범주를 모델 입력으로 표현한 값이다. 숫자의 크고 작음이 우열을 뜻하지 않으며, "
            "전처리 단계에서 사용한 인코딩 규칙과 함께 해석해야 한다."
        ),
    },
    {
        "id": "feature-channel-recent-median-views",
        "title": "channel_recent_median_views",
        "aliases": ["최근 중앙 조회수", "채널 기준 조회수", "median views"],
        "topic": "model_feature",
        "content": (
            "channel_recent_median_views는 해당 채널의 최근 영상 조회수 중앙값이다. "
            "극단적으로 높은 영상의 영향을 줄이면서 채널의 평소 성과 기준선을 표현한다."
        ),
    },
    {
        "id": "feature-trend-score",
        "title": "food_keyword_trend_score",
        "aliases": ["트렌드 점수", "키워드 유행", "trend score"],
        "topic": "model_feature",
        "content": (
            "food_keyword_trend_score는 음식 키워드가 현재 얼마나 관심을 받는지를 나타내도록 설계한 피처다. "
            "정확한 데이터 출처·기간·정규화 방식은 팀의 최종 피처 정의서가 확정되면 그 정의를 우선한다."
        ),
    },
    {
        "id": "feature-season-match-score",
        "title": "season_match_score",
        "aliases": ["계절 적합도", "시즌 점수", "season match"],
        "topic": "model_feature",
        "content": (
            "season_match_score는 콘텐츠 주제와 현재 계절의 적합도를 표현하도록 설계한 피처다. "
            "SHAP 값이 양수일 때 해당 예측에서 점수 상승 방향으로 작용했다고 설명할 수 있다."
        ),
    },
    {
        "id": "feature-same-food-upload-count-24h",
        "title": "same_food_upload_count_24h",
        "aliases": ["24시간 경쟁 영상", "동일 음식 업로드", "경쟁도"],
        "topic": "model_feature",
        "content": (
            "same_food_upload_count_24h는 최근 24시간 동안 같은 음식 주제로 올라온 영상 수다. "
            "동시 업로드가 많을수록 경쟁이 높을 가능성을 나타내지만, SHAP 방향은 실제 예측 결과를 확인해야 한다."
        ),
    },
    {
        "id": "feature-weather-food-match-score",
        "title": "weather_food_match_score",
        "aliases": ["날씨 음식 적합도", "기온", "습도", "weather match"],
        "topic": "model_feature",
        "content": (
            "weather_food_match_score는 날씨와 음식 주제의 적합도를 표현하도록 설계한 피처다. "
            "날씨가 조회수의 원인이라고 단정할 수 없고, 피처 계산식과 SHAP 값을 함께 확인해야 한다."
        ),
    },
    {
        "id": "product-identity",
        "title": "유바씨(YouTube Viral Signal)",
        "aliases": ["PredictTube", "유바씨", "YouTube Viral Signal", "이 서비스", "이 앱"],
        "topic": "product_faq",
        "content": (
            "유바씨(YouTube Viral Signal)는 유튜브 채널과 영상의 데이터를 분석해 바이럴 가능성을 "
            "예측하고, 채널 성과 대시보드와 AI 챗봇 인사이트를 제공하는 데이터 기반 유튜브 분석 서비스다."
        ),
    },
    {
        "id": "product-shorts-support",
        "title": "쇼츠 영상 분석 지원 여부",
        "aliases": ["쇼츠", "Shorts", "숏폼"],
        "topic": "product_faq",
        "content": (
            "쇼츠(Shorts) 형식 영상은 현재 바이럴 점수 예측 대상에서 제외된다. "
            "일반 영상(롱폼) URL만 예측에 사용할 수 있다."
        ),
    },
    {
        "id": "product-analyzable-video-scope",
        "title": "예측 가능한 영상 범위",
        "aliases": ["업로드 전 영상", "아직 안 올린 영상", "게시 전 영상"],
        "topic": "product_faq",
        "content": (
            "바이럴 점수 예측은 유튜브에 이미 게시되어 실제 URL이 존재하는 영상만 가능하다. "
            "아직 업로드하지 않은 영상은 URL이 없어 예측할 수 없다."
        ),
    },
    {
        "id": "product-prediction-scope-and-chat-scope",
        "title": "예측 실행 조건과 챗봇 조회 범위",
        "aliases": ["채널 연동", "로그인", "URL 입력", "예측한 영상 정보", "챗봇 조회"],
        "topic": "product_faq",
        "content": (
            "로그인한 사용자는 자신의 채널을 연동하지 않아도 유튜브 영상 URL과 카테고리만 입력하면 "
            "바이럴 점수 예측을 실행할 수 있다. 다만 AI 챗봇 질문·답변은 사용자가 연동한 채널의 영상 "
            "범위 안에서만 동작하므로, 채널에 연동되지 않은 영상은 예측은 가능해도 챗봇에게 그 영상에 "
            "대해 물어보면 정보를 얻을 수 없다."
        ),
    },
    {
        "id": "product-lab-video-insights",
        "title": "실험실 - 영상 인사이트",
        "aliases": ["실험실", "영상 인사이트", "성과 분포", "Lab", "조회수 참여율 분포"],
        "topic": "product_faq",
        "content": (
            "실험실의 '영상 인사이트' 화면은 채널 영상들의 성과 분포를 x축 조회수, y축 참여율의 "
            "산점도로 보여준다. 이를 통해 조회수와 참여율이 높은 영상이 실제로 바이럴 점수도 높은지 "
            "시각적으로 비교해 확인할 수 있다."
        ),
    },
]


def embedding_text(document: dict[str, Any]) -> str:
    aliases = ", ".join(document.get("aliases") or [])
    return f"제목: {document['title']}\n관련 용어: {aliases}\n설명: {document['content']}"


def seed_documents() -> list[dict[str, Any]]:
    return [
        {
            **document,
            "channel_id": "GLOBAL",
            "doc_type": "feature_metric_definition",
            "knowledge_version": KNOWLEDGE_VERSION,
            "schema_version": "2.0.0",
        }
        for document in KNOWLEDGE_DOCUMENTS
    ]


def lexical_search(question: str, limit: int = 5) -> list[dict[str, Any]]:
    return lexical_rank_documents(question, seed_documents(), limit=limit)
