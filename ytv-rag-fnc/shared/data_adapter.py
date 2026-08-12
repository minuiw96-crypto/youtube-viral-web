"""Normalize evolving Cosmos documents into one stable RAG contract."""

from __future__ import annotations

from typing import Any


def _first(document: dict[str, Any] | None, *names: str) -> Any:
    if not document:
        return None
    for name in names:
        value = document.get(name)
        if value is not None:
            return value
    return None


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def normalize_video(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if not document:
        return None
    nested = document.get("video") if isinstance(document.get("video"), dict) else {}
    youtube_raw = document.get("youtube_raw") if isinstance(document.get("youtube_raw"), dict) else {}
    system = document.get("system") if isinstance(document.get("system"), dict) else {}
    snippet = youtube_raw.get("snippet") if isinstance(youtube_raw.get("snippet"), dict) else {}
    content_details = (
        youtube_raw.get("contentDetails")
        if isinstance(youtube_raw.get("contentDetails"), dict)
        else {}
    )
    source = {
        **document,
        **system,
        **youtube_raw,
        **snippet,
        **content_details,
        **nested,
    }
    return {
        "video_id": _first(source, "video_id", "id"),
        "channel_id": _first(source, "channel_id"),
        "channel_title": _first(
            source, "channel_title", "channel_name", "channelTitle"
        ),
        "title": _first(source, "title"),
        "description": _first(source, "description"),
        "published_at": _first(
            source, "published_at", "published_at_utc", "publishedAt"
        ),
        "duration_seconds": _first(source, "duration_seconds"),
        "content_domain": _first(source, "content_domain", "category"),
        "project_category": _first(source, "project_category"),
        "system": _first(source, "system"),
        "first_collected_at": _first(source, "first_collected_at", "collected_at"),
        "thumbnail_blob_path": _first(source, "thumbnail_blob_path"),
        "thumbnail_url": _first(
            source,
            "thumbnail_url",
            "thumbnailUrl",
            "thumbnail_maxres_url",
            "thumbnail_standard_url",
            "thumbnail_high_url",
            "thumbnail_medium_url",
            "thumbnail_default_url",
        ),
        "video_url": _first(source, "video_url", "url"),
        "food_keyword": _first(source, "food_keyword"),
        "is_eligible": _first(source, "is_eligible"),
        "exclusion_reasons": _as_list(_first(source, "exclusion_reasons")),
        "subscriber_count": _first(source, "subscriber_count"),
        "channel_total_view_count": _first(
            source, "channel_total_view_count", "channel_total_views"
        ),
        "public_video_count": _first(
            source, "public_video_count", "channel_video_count"
        ),
    }


def _normalize_effects(document: dict[str, Any]) -> dict[str, Any]:
    explanation = (
        document.get("local_explanation")
        if isinstance(document.get("local_explanation"), dict)
        else {}
    )
    values = []
    for row in _as_list(explanation.get("values")):
        if not isinstance(row, dict):
            continue
        impact = _first(row, "impact", "shap_value", "effect_value")
        direction = _first(row, "direction", "effect_direction")
        if not direction and isinstance(impact, (int, float)):
            direction = "positive" if impact >= 0 else "negative"
        values.append(
            {
                "feature": _first(row, "feature", "feature_name"),
                "value": _first(row, "value", "feature_value"),
                "impact": impact,
                "direction": direction,
                "rank": _first(row, "rank", "effect_rank"),
            }
        )

    positive = _as_list(document.get("top_positive_factors"))
    negative = _as_list(document.get("top_negative_factors"))
    if values:
        positive = [row["feature"] for row in values if row["direction"] == "positive"]
        negative = [row["feature"] for row in values if row["direction"] == "negative"]

    return {
        "method": explanation.get("method") or document.get("local_explanation_method") or "ranked_factors",
        "has_numeric_impacts": bool(values),
        "values": values,
        "positive_factors": positive,
        "negative_factors": negative,
    }


def normalize_prediction(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if not document:
        return None
    nested = document.get("prediction") if isinstance(document.get("prediction"), dict) else {}
    source = {**document, **nested}
    input_features = (
        document.get("input_features")
        if isinstance(document.get("input_features"), dict)
        else document.get("feature_values")
        if isinstance(document.get("feature_values"), dict)
        else {}
    )
    return {
        "video_id": _first(source, "video_id"),
        "candidate_batch_id": _first(source, "candidate_batch_id"),
        "channel_id": _first(source, "channel_id"),
        "model_name": _first(source, "model_name"),
        "model_version": _first(source, "model_version"),
        "raw_prediction": _first(
            source, "raw_prediction", "predicted_relative_log_performance"
        ),
        "viral_score": _first(
            source, "viral_score", "viral_score_0_100", "predicted_score"
        ),
        "viral_grade": _first(source, "viral_grade"),
        "category_percentile": _first(source, "category_percentile"),
        "rank": _first(source, "rank", "candidate_rank"),
        "candidate_count": _first(source, "candidate_count"),
        "expected_performance_multiplier": _first(
            source, "expected_performance_multiplier", "expected_relative_performance"
        ),
        "estimated_72h_views": _first(source, "estimated_72h_views"),
        "baseline_72h_views": _first(
            source, "baseline_72h_views", "channel_baseline_72h_views"
        ),
        "estimated_7d_views": _first(source, "estimated_7d_views"),
        "baseline_7d_views": _first(source, "baseline_7d_views"),
        "prediction_age_hours": _first(source, "prediction_age_hours"),
        "predicted_at": _first(source, "predicted_at"),
        "score_definition": _first(source, "score_definition"),
        "label_basis": _first(source, "label_basis"),
        "input_features": input_features,
        "explanation": _normalize_effects(document),
    }


def normalize_snapshot(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "video_id": _first(document, "video_id"),
        "channel_id": _first(document, "channel_id"),
        "target_age_hours": _first(document, "target_age_hours", "age_hours"),
        "actual_age_hours": _first(document, "actual_age_hours"),
        "view_count": _first(document, "view_count", "views"),
        "like_count": _first(document, "like_count", "likes"),
        "comment_count": _first(document, "comment_count", "comments"),
        "favorite_count": _first(document, "favorite_count"),
        "engagement_rate": _first(document, "engagement_rate"),
        "view_velocity": _first(document, "view_velocity"),
        "collected_at": _first(
            document, "collected_at", "observed_at", "snapshot_time"
        ),
    }


def normalize_channel_snapshot(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "channel_id": _first(document, "channel_id"),
        "subscriber_count": _first(document, "subscriber_count", "subscribers"),
        "video_count": _first(document, "video_count", "public_video_count"),
        "view_count": _first(document, "view_count", "channel_total_view_count"),
        "subscriber_growth_rate": _first(document, "subscriber_growth_rate"),
        "view_growth_rate": _first(document, "view_growth_rate"),
        "snapshot_time": _first(
            document, "snapshot_time", "collected_at", "observed_at"
        ),
    }


def normalize_evaluation(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if not document:
        return None
    return {
        "video_id": _first(document, "video_id"),
        "channel_id": _first(document, "channel_id"),
        "candidate_batch_id": _first(document, "candidate_batch_id"),
        "model_version": _first(document, "model_version"),
        "evaluation_target_hours": _first(document, "evaluation_target_hours"),
        "label_score": _first(document, "label_score"),
        "label_version": _first(document, "label_version"),
        "target_horizon": _first(document, "target_horizon"),
        "features_version": _first(document, "features_version"),
        "estimated_views": _first(document, "estimated_views", "predicted_views"),
        "actual_views": _first(document, "actual_views", "observed_views"),
        "absolute_error": _first(document, "absolute_error"),
        "absolute_percentage_error": _first(document, "absolute_percentage_error"),
        "predicted_top3_video_ids": _as_list(document.get("predicted_top3_video_ids")),
        "actual_top3_video_ids": _as_list(document.get("actual_top3_video_ids")),
        "spearman": _first(document, "spearman"),
        "ndcg_at_3": _first(document, "ndcg_at_3"),
        "precision_at_3": _first(document, "precision_at_3"),
        "hit_rate_at_3": _first(document, "hit_rate_at_3"),
        "evaluated_at": _first(document, "evaluated_at", "calculated_at"),
    }
