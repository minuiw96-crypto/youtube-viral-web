"""Deterministic metric calculations for category-scoped RAG context."""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import median
from typing import Any, Callable


FORMULA_VERSION = "v1"


def as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().replace(",", ""))
        except ValueError:
            return None
    return None


def _rounded(value: float | None, digits: int = 4) -> float | None:
    return round(value, digits) if value is not None else None


def metric_result(
    value: float | None,
    *,
    unit: str,
    source: str,
    formula: str,
    inputs: dict[str, Any] | None = None,
    period: str | None = None,
) -> dict[str, Any]:
    return {
        "value": _rounded(value),
        "unit": unit,
        "source": source,
        "formula": formula,
        "formula_version": FORMULA_VERSION,
        "period": period,
        "inputs": inputs or {},
        "available": value is not None,
    }


def stored_or_calculated(
    stored_value: Any,
    calculate: Callable[[], float | None],
    *,
    unit: str,
    formula: str,
    inputs: dict[str, Any] | None = None,
    period: str | None = None,
) -> dict[str, Any]:
    stored = as_number(stored_value)
    if stored is not None:
        return metric_result(
            stored,
            unit=unit,
            source="stored",
            formula=formula,
            inputs=inputs,
            period=period,
        )
    return metric_result(
        calculate(),
        unit=unit,
        source="calculated",
        formula=formula,
        inputs=inputs,
        period=period,
    )


def growth_rate(previous: Any, current: Any) -> float | None:
    previous_number = as_number(previous)
    current_number = as_number(current)
    if previous_number is None or current_number is None or previous_number == 0:
        return None
    return ((current_number - previous_number) / previous_number) * 100


def difference(previous: Any, current: Any) -> float | None:
    previous_number = as_number(previous)
    current_number = as_number(current)
    if previous_number is None or current_number is None:
        return None
    return current_number - previous_number


def engagement_rate(views: Any, likes: Any, comments: Any) -> float | None:
    view_count = as_number(views)
    like_count = as_number(likes)
    comment_count = as_number(comments)
    if view_count is None or view_count <= 0:
        return None
    return ((like_count or 0) + (comment_count or 0)) / view_count * 100


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _snapshot_position(snapshot: dict[str, Any]) -> tuple[float, str]:
    age = as_number(snapshot.get("actual_age_hours"))
    if age is None:
        age = as_number(snapshot.get("target_age_hours"))
    if age is not None:
        return age, "age_hours"
    timestamp = _parse_time(snapshot.get("collected_at") or snapshot.get("snapshot_time"))
    return (timestamp.timestamp() / 3600, "timestamp") if timestamp else (float("-inf"), "unknown")


def ordered_snapshots(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(snapshots, key=lambda row: _snapshot_position(row)[0])


def view_velocity(snapshots: list[dict[str, Any]]) -> tuple[float | None, dict[str, Any]]:
    valid = [row for row in ordered_snapshots(snapshots) if as_number(row.get("view_count")) is not None]
    if len(valid) < 2:
        return None, {}
    first, latest = valid[0], valid[-1]
    first_position, first_kind = _snapshot_position(first)
    latest_position, latest_kind = _snapshot_position(latest)
    if (
        first_kind == "unknown"
        or latest_kind == "unknown"
        or first_kind != latest_kind
        or latest_position <= first_position
    ):
        return None, {}
    first_views = as_number(first.get("view_count"))
    latest_views = as_number(latest.get("view_count"))
    elapsed_hours = latest_position - first_position
    return (
        (latest_views - first_views) / elapsed_hours,
        {
            "first_view_count": first_views,
            "latest_view_count": latest_views,
            "elapsed_hours": _rounded(elapsed_hours),
        },
    )


def prediction_comparison(predicted: Any, actual: Any, stored_absolute_error: Any = None) -> dict[str, Any]:
    predicted_number = as_number(predicted)
    actual_number = as_number(actual)
    if predicted_number is None or actual_number is None:
        return {
            "available": False,
            "predicted": predicted_number,
            "actual": actual_number,
            "error": None,
            "absolute_error": metric_result(
                None,
                unit="score_point",
                source="calculated",
                formula="abs(actual - predicted)",
            ),
            "absolute_percentage_error": metric_result(
                None,
                unit="percent",
                source="calculated",
                formula="abs(actual - predicted) / abs(actual) * 100",
            ),
            "direction": None,
        }

    error = actual_number - predicted_number
    absolute_error = stored_or_calculated(
        stored_absolute_error,
        lambda: abs(error),
        unit="score_point",
        formula="abs(actual - predicted)",
        inputs={"predicted": predicted_number, "actual": actual_number},
    )
    percentage = abs(error) / abs(actual_number) * 100 if actual_number != 0 else None
    return {
        "available": True,
        "predicted": predicted_number,
        "actual": actual_number,
        "error": _rounded(error),
        "absolute_error": absolute_error,
        "absolute_percentage_error": metric_result(
            percentage,
            unit="percent",
            source="calculated",
            formula="abs(actual - predicted) / abs(actual) * 100",
            inputs={"predicted": predicted_number, "actual": actual_number},
        ),
        "direction": "under_prediction" if error > 0 else "over_prediction" if error < 0 else "matched",
    }


def _latest_snapshot(snapshots: list[dict[str, Any]]) -> dict[str, Any] | None:
    ordered = ordered_snapshots(snapshots)
    return ordered[-1] if ordered else None


def channel_growth_metrics(context: dict[str, Any], period: str | None) -> dict[str, Any]:
    snapshots = ordered_snapshots(context.get("channel_snapshots") or [])
    if len(snapshots) < 2:
        return {"available": False, "reason": "채널 스냅샷이 2개 이상 필요합니다."}
    first, latest = snapshots[0], snapshots[-1]
    return {
        "available": True,
        "period": period or "available_snapshot_range",
        "first_snapshot_time": first.get("snapshot_time"),
        "latest_snapshot_time": latest.get("snapshot_time"),
        "subscriber_growth_rate": stored_or_calculated(
            latest.get("subscriber_growth_rate"),
            lambda: growth_rate(first.get("subscriber_count"), latest.get("subscriber_count")),
            unit="percent",
            formula="(current_subscribers - previous_subscribers) / previous_subscribers * 100",
            inputs={
                "previous_subscribers": first.get("subscriber_count"),
                "current_subscribers": latest.get("subscriber_count"),
            },
            period=period or "available_snapshot_range",
        ),
        "view_growth_rate": stored_or_calculated(
            latest.get("view_growth_rate"),
            lambda: growth_rate(first.get("view_count"), latest.get("view_count")),
            unit="percent",
            formula="(current_views - previous_views) / previous_views * 100",
            inputs={
                "previous_views": first.get("view_count"),
                "current_views": latest.get("view_count"),
            },
            period=period or "available_snapshot_range",
        ),
        "subscriber_change": _rounded(
            difference(first.get("subscriber_count"), latest.get("subscriber_count"))
        ),
        "view_change": _rounded(
            difference(first.get("view_count"), latest.get("view_count"))
        ),
    }


def video_performance_metrics(selected: dict[str, Any]) -> dict[str, Any]:
    snapshots = selected.get("snapshots") or []
    latest = _latest_snapshot(snapshots)
    if not latest:
        return {"available": False, "reason": "영상 스냅샷이 없습니다."}
    velocity, velocity_inputs = view_velocity(snapshots)
    first = ordered_snapshots(snapshots)[0]
    return {
        "available": True,
        "latest_snapshot": latest,
        "view_growth_rate": metric_result(
            growth_rate(first.get("view_count"), latest.get("view_count")),
            unit="percent",
            source="calculated",
            formula="(latest_views - first_views) / first_views * 100",
            inputs={
                "first_views": first.get("view_count"),
                "latest_views": latest.get("view_count"),
            },
        ),
        "engagement_rate": stored_or_calculated(
            latest.get("engagement_rate"),
            lambda: engagement_rate(
                latest.get("view_count"),
                latest.get("like_count"),
                latest.get("comment_count"),
            ),
            unit="percent",
            formula="(likes + comments) / views * 100",
            inputs={
                "views": latest.get("view_count"),
                "likes": latest.get("like_count"),
                "comments": latest.get("comment_count"),
            },
        ),
        "view_velocity": stored_or_calculated(
            latest.get("view_velocity"),
            lambda: velocity,
            unit="views_per_hour",
            formula="(latest_views - first_views) / elapsed_hours",
            inputs=velocity_inputs,
        ),
    }


def _candidate_metric(candidate: dict[str, Any], metric: str) -> float | None:
    prediction = candidate.get("prediction") or {}
    evaluation = candidate.get("evaluation") or {}
    snapshot = candidate.get("latest_snapshot") or {}
    values = {
        "viral_score": prediction.get("viral_score"),
        "label_score": evaluation.get("label_score"),
        "view_count": snapshot.get("view_count"),
        "like_count": snapshot.get("like_count"),
        "comment_count": snapshot.get("comment_count"),
        "engagement_rate": snapshot.get("engagement_rate"),
        "view_velocity": snapshot.get("view_velocity"),
    }
    if metric == "absolute_error":
        stored_error = as_number(evaluation.get("absolute_error"))
        if stored_error is not None:
            return abs(stored_error)
        predicted = as_number(prediction.get("viral_score"))
        actual = as_number(evaluation.get("label_score"))
        return abs(actual - predicted) if predicted is not None and actual is not None else None
    if metric == "engagement_rate" and as_number(values[metric]) is None:
        return engagement_rate(
            snapshot.get("view_count"),
            snapshot.get("like_count"),
            snapshot.get("comment_count"),
        )
    return as_number(values.get(metric))


def ranking_metrics(candidates: list[dict[str, Any]], metric: str | None) -> dict[str, Any]:
    ranking_metric = metric if metric in {
        "viral_score",
        "label_score",
        "view_count",
        "like_count",
        "comment_count",
        "engagement_rate",
        "view_velocity",
        "absolute_error",
    } else "viral_score"
    ranked = []
    for candidate in candidates:
        value = _candidate_metric(candidate, ranking_metric)
        if value is None:
            continue
        video = candidate.get("video") or {}
        ranked.append(
            {
                "video_id": video.get("video_id"),
                "title": video.get("title"),
                "value": _rounded(value),
            }
        )
    ranked.sort(key=lambda row: row["value"], reverse=True)
    for index, row in enumerate(ranked, 1):
        row["rank"] = index
    return {
        "available": bool(ranked),
        "metric": ranking_metric,
        "candidate_count": len(ranked),
        "top_n": ranked[:10],
    }


def model_evaluation_metrics(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize prediction accuracy only across videos with both scores."""
    comparisons = []
    for candidate in candidates:
        prediction = candidate.get("prediction") or {}
        evaluation = candidate.get("evaluation") or {}
        comparison = prediction_comparison(
            prediction.get("viral_score"),
            evaluation.get("label_score"),
            evaluation.get("absolute_error"),
        )
        if not comparison.get("available"):
            continue
        video = candidate.get("video") or {}
        comparisons.append(
            {
                "video_id": video.get("video_id"),
                "title": video.get("title"),
                "predicted": comparison["predicted"],
                "actual": comparison["actual"],
                "error": comparison["error"],
                "absolute_error": comparison["absolute_error"]["value"],
                "absolute_percentage_error": comparison["absolute_percentage_error"]["value"],
            }
        )
    if not comparisons:
        return {
            "available": False,
            "evaluated_video_count": 0,
            "reason": "예측 점수와 실제 성과 점수가 모두 있는 영상이 필요합니다.",
        }
    absolute_errors = [row["absolute_error"] for row in comparisons]
    percentage_errors = [
        row["absolute_percentage_error"]
        for row in comparisons
        if row["absolute_percentage_error"] is not None
    ]
    return {
        "available": True,
        "evaluated_video_count": len(comparisons),
        "mean_absolute_error": metric_result(
            sum(absolute_errors) / len(absolute_errors),
            unit="score_point",
            source="calculated",
            formula="sum(abs(actual - predicted)) / evaluated_videos",
        ),
        "mean_absolute_percentage_error": metric_result(
            sum(percentage_errors) / len(percentage_errors) if percentage_errors else None,
            unit="percent",
            source="calculated",
            formula="mean(abs(actual - predicted) / abs(actual) * 100)",
        ),
        "comparisons": comparisons,
    }


def baseline_comparison_metrics(context: dict[str, Any], metric: str | None) -> dict[str, Any]:
    selected = context.get("selected_video") or {}
    selected_video_id = str((selected.get("video") or {}).get("video_id") or "")
    candidates = context.get("comparison_videos") or []
    selected_candidate = next(
        (
            candidate
            for candidate in candidates
            if str((candidate.get("video") or {}).get("video_id") or "") == selected_video_id
        ),
        None,
    )
    comparison_metric = metric or "viral_score"
    selected_value = _candidate_metric(selected_candidate or {}, comparison_metric)
    comparison_values = [
        value
        for candidate in candidates
        if str((candidate.get("video") or {}).get("video_id") or "") != selected_video_id
        if (value := _candidate_metric(candidate, comparison_metric)) is not None
    ]
    if selected_value is None or not comparison_values:
        return {
            "available": False,
            "metric": comparison_metric,
            "reason": "선택 영상 값 또는 비교할 같은 채널 영상 값이 부족합니다.",
        }
    baseline = float(median(comparison_values))
    difference = selected_value - baseline
    difference_rate = difference / baseline * 100 if baseline != 0 else None
    return {
        "available": True,
        "metric": comparison_metric,
        "selected_value": _rounded(selected_value),
        "channel_median": _rounded(baseline),
        "difference": _rounded(difference),
        "difference_rate": metric_result(
            difference_rate,
            unit="percent",
            source="calculated",
            formula="(selected_value - channel_median) / channel_median * 100",
            inputs={"selected_value": selected_value, "channel_median": baseline},
        ),
        "comparison_video_count": len(comparison_values),
    }


def data_status_metrics(status: dict[str, Any]) -> dict[str, Any]:
    video_count = int(as_number(status.get("video_count")) or 0)
    videos = status.get("videos") or []
    prediction_video_count = sum(1 for row in videos if row.get("has_prediction") is True)
    label_video_count = sum(1 for row in videos if row.get("has_label") is True)
    snapshot_video_count = sum(
        1 for row in videos if int(as_number(row.get("snapshot_count")) or 0) > 0
    )

    def coverage(count: int) -> float | None:
        return count / video_count * 100 if video_count else None

    return {
        "available": video_count > 0,
        "video_count": video_count,
        "prediction_coverage": metric_result(
            coverage(prediction_video_count),
            unit="percent",
            source="calculated",
            formula="videos_with_prediction / videos * 100",
            inputs={
                "videos_with_prediction": prediction_video_count,
                "videos": video_count,
            },
        ),
        "label_coverage": metric_result(
            coverage(label_video_count),
            unit="percent",
            source="calculated",
            formula="videos_with_label / videos * 100",
            inputs={"videos_with_label": label_video_count, "videos": video_count},
        ),
        "snapshot_coverage": metric_result(
            coverage(snapshot_video_count),
            unit="percent",
            source="calculated",
            formula="videos_with_snapshot / videos * 100",
            inputs={
                "videos_with_snapshot": snapshot_video_count,
                "videos": video_count,
            },
        ),
    }


def calculate_context_metrics(
    context: dict[str, Any] | None,
    question_analysis: dict[str, Any],
) -> dict[str, Any]:
    if not context:
        return {}
    categories = context.get("categories") or [question_analysis.get("primary_category")]
    metric = question_analysis.get("metric")
    period = question_analysis.get("period")
    results: dict[str, Any] = {}

    if "channel_growth" in categories:
        results["channel_growth"] = channel_growth_metrics(context, period)
    if "video_performance" in categories:
        results["video_performance"] = video_performance_metrics(
            context.get("selected_video") or {}
        )
    if "prediction_score" in categories:
        prediction = (context.get("selected_video") or {}).get("prediction") or {}
        selected_video_id = str(
            (((context.get("selected_video") or {}).get("video") or {}).get("video_id"))
            or ""
        )
        cohort = sorted(
            context.get("prediction_cohort") or [],
            key=lambda row: as_number(row.get("viral_score")) or float("-inf"),
            reverse=True,
        )
        cohort_rank = next(
            (index for index, row in enumerate(cohort, 1) if str(row.get("video_id")) == selected_video_id),
            None,
        )
        results["prediction_score"] = {
            "available": prediction.get("viral_score") is not None,
            "viral_score": prediction.get("viral_score"),
            "rank": cohort_rank,
            "candidate_count": len(cohort),
            "total_video_count": int(context.get("total_video_count") or 0),
            "comparison_population": "videos_with_prediction_score",
        }
    if "shap_factors" in categories:
        explanation = (
            ((context.get("selected_video") or {}).get("prediction") or {}).get("explanation")
            or {}
        )
        results["shap_factors"] = {
            "available": bool(explanation.get("values") or explanation.get("positive_factors") or explanation.get("negative_factors")),
            "method": explanation.get("method"),
            "has_numeric_impacts": explanation.get("has_numeric_impacts", False),
            "positive_factor_count": len(explanation.get("positive_factors") or []),
            "negative_factor_count": len(explanation.get("negative_factors") or []),
        }
    if "prediction_vs_actual" in categories:
        selected = context.get("selected_video") or {}
        prediction = selected.get("prediction") or {}
        evaluation = selected.get("evaluation") or {}
        results["prediction_vs_actual"] = prediction_comparison(
            prediction.get("viral_score"),
            evaluation.get("label_score"),
            evaluation.get("absolute_error"),
        )
    if "video_ranking" in categories:
        results["video_ranking"] = ranking_metrics(
            context.get("ranking_candidates") or [], metric
        )
        results["video_ranking"]["total_video_count"] = int(
            context.get("total_video_count") or 0
        )
        results["video_ranking"]["comparison_population"] = "videos_with_selected_metric"
    if "model_evaluation" in categories:
        results["model_evaluation"] = model_evaluation_metrics(
            context.get("ranking_candidates") or []
        )
        results["model_evaluation"]["total_video_count"] = int(
            context.get("total_video_count") or 0
        )
    if "channel_baseline_comparison" in categories:
        results["channel_baseline_comparison"] = baseline_comparison_metrics(
            context, metric
        )
    if "data_status" in categories:
        results["data_status"] = data_status_metrics(context.get("data_status") or {})
    return results
