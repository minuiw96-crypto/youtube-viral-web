"""Build compact, auditable metadata for the final RAG answer."""

from __future__ import annotations

from typing import Any


def _unavailable_metric_paths(value: Any, prefix: str = "") -> list[str]:
    if isinstance(value, dict):
        if value.get("available") is False:
            return [prefix.rstrip(".") or "unknown"]
        paths: list[str] = []
        for key, child in value.items():
            child_prefix = f"{prefix}{key}."
            paths.extend(_unavailable_metric_paths(child, child_prefix))
        return paths
    if isinstance(value, list):
        paths = []
        for index, child in enumerate(value):
            paths.extend(_unavailable_metric_paths(child, f"{prefix}{index}."))
        return paths
    return []


def build_evidence_summary(
    channel_context: dict[str, Any] | None,
    question_analysis: dict[str, Any],
    computed_metrics: dict[str, Any],
    knowledge: list[dict[str, Any]],
    retrieval_mode: str,
) -> dict[str, Any]:
    selected = (channel_context or {}).get("selected_video") or {}
    video = selected.get("video") or {}
    return {
        "primary_category": question_analysis.get("primary_category"),
        "secondary_categories": question_analysis.get("secondary_categories") or [],
        "operational_data_sources": (channel_context or {}).get("data_sources") or [],
        "selected_video": (
            {"video_id": video.get("video_id"), "title": video.get("title")}
            if video
            else None
        ),
        "computed_metric_sections": sorted(computed_metrics),
        "unavailable_metrics": sorted(set(_unavailable_metric_paths(computed_metrics))),
        "knowledge_retrieval_mode": retrieval_mode,
        "knowledge_references": [
            {
                "id": row.get("id"),
                "title": row.get("title"),
                "similarity": row.get("similarity"),
            }
            for row in knowledge
        ],
    }


RESPONSE_CONTRACT = {
    "language": "ko-KR",
    "audience": "YouTube 데이터와 머신러닝을 처음 접하는 사용자",
    "mode": "질문에서 상세 설명을 요청한 경우에만 detailed, 그 외에는 brief",
    "structure": {
        "conclusion": "질문에 대한 직접 답변 한 문장",
        "key_points": "질문과 직접 관련된 핵심 근거만 기본 최대 3개",
        "limitation": "결론에 영향을 주는 제한사항이 있을 때만 한 문장",
    },
    "rules": [
        "제공된 근거에 없는 수치와 사실을 만들지 않는다.",
        "내부 JSON 경로, 변수명, 테이블명과 시스템 용어를 노출하지 않는다.",
        "데이터 항목 이름은 질문에 포함되어 있어도 반복하지 않고 쉬운 의미로 바꾼다.",
        "질문과 관계없는 정보와 데이터 부족 설명을 덧붙이지 않는다.",
        "같은 결론이나 수치를 반복하지 않는다.",
        "비교 기준이 없으면 빠르다, 높다, 상위권처럼 상대 평가하지 않는다.",
        "영상 제목이나 주제로 데이터에 없는 비교 집단을 만들지 않는다.",
        "다른 채널의 정보는 언급하지 않는다.",
        "바이럴 점수를 성공 확률로 표현하지 않는다.",
        "SHAP 방향을 인과관계로 단정하지 않는다.",
        "사용할 수 없는 값은 추측하지 않는다.",
    ],
}
