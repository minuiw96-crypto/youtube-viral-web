"""Tests for deterministic RAG metric calculations."""

import unittest

from shared.metrics import (
    baseline_comparison_metrics,
    channel_growth_metrics,
    data_status_metrics,
    engagement_rate,
    growth_rate,
    prediction_comparison,
    model_evaluation_metrics,
    ranking_metrics,
    stored_or_calculated,
    video_performance_metrics,
    view_velocity,
)


class PrimitiveMetricTests(unittest.TestCase):
    def test_growth_rate(self):
        self.assertEqual(growth_rate(100, 120), 20)
        self.assertIsNone(growth_rate(0, 120))
        self.assertIsNone(growth_rate(None, 120))

    def test_engagement_rate(self):
        self.assertEqual(engagement_rate(1000, 40, 10), 5)
        self.assertIsNone(engagement_rate(0, 40, 10))

    def test_stored_value_has_priority(self):
        result = stored_or_calculated(
            12.5,
            lambda: 99,
            unit="percent",
            formula="test formula",
        )
        self.assertEqual(result["value"], 12.5)
        self.assertEqual(result["source"], "stored")
        self.assertEqual(result["formula_version"], "v1")

    def test_view_velocity(self):
        value, inputs = view_velocity(
            [
                {"target_age_hours": 1, "view_count": 100},
                {"target_age_hours": 6, "view_count": 600},
            ]
        )
        self.assertEqual(value, 100)
        self.assertEqual(inputs["elapsed_hours"], 5)


class CategoryMetricTests(unittest.TestCase):
    def test_channel_growth_uses_stored_rate_but_calculates_changes(self):
        result = channel_growth_metrics(
            {
                "channel_snapshots": [
                    {
                        "snapshot_time": "2026-08-01T00:00:00Z",
                        "subscriber_count": 100,
                        "view_count": 1000,
                    },
                    {
                        "snapshot_time": "2026-08-02T00:00:00Z",
                        "subscriber_count": 120,
                        "view_count": 1500,
                        "subscriber_growth_rate": 25,
                    },
                ]
            },
            "1d",
        )
        self.assertEqual(result["subscriber_growth_rate"]["value"], 25)
        self.assertEqual(result["subscriber_growth_rate"]["source"], "stored")
        self.assertEqual(result["view_growth_rate"]["value"], 50)
        self.assertEqual(result["view_growth_rate"]["source"], "calculated")
        self.assertEqual(result["subscriber_change"], 20)

    def test_missing_channel_count_does_not_become_zero(self):
        result = channel_growth_metrics(
            {
                "channel_snapshots": [
                    {"snapshot_time": "2026-08-01T00:00:00Z"},
                    {"snapshot_time": "2026-08-02T00:00:00Z", "subscriber_count": 120},
                ]
            },
            None,
        )
        self.assertIsNone(result["subscriber_change"])

    def test_video_performance(self):
        result = video_performance_metrics(
            {
                "snapshots": [
                    {"target_age_hours": 1, "view_count": 100, "like_count": 5},
                    {
                        "target_age_hours": 6,
                        "view_count": 600,
                        "like_count": 24,
                        "comment_count": 6,
                    },
                ]
            }
        )
        self.assertEqual(result["view_growth_rate"]["value"], 500)
        self.assertEqual(result["engagement_rate"]["value"], 5)
        self.assertEqual(result["view_velocity"]["value"], 100)

    def test_prediction_comparison(self):
        result = prediction_comparison(80, 70)
        self.assertEqual(result["error"], -10)
        self.assertEqual(result["absolute_error"]["value"], 10)
        self.assertEqual(result["direction"], "over_prediction")
        self.assertEqual(result["absolute_percentage_error"]["value"], 14.2857)

    def test_ranking(self):
        candidates = [
            {"video": {"video_id": "a", "title": "A"}, "prediction": {"viral_score": 20}},
            {"video": {"video_id": "b", "title": "B"}, "prediction": {"viral_score": 80}},
        ]
        result = ranking_metrics(candidates, "viral_score")
        self.assertEqual(result["top_n"][0]["video_id"], "b")
        self.assertEqual(result["top_n"][0]["rank"], 1)

    def test_prediction_error_ranking(self):
        candidates = [
            {
                "video": {"video_id": "a", "title": "A"},
                "prediction": {"viral_score": 80},
                "evaluation": {"label_score": 78},
            },
            {
                "video": {"video_id": "b", "title": "B"},
                "prediction": {"viral_score": 50},
                "evaluation": {"label_score": 75},
            },
        ]
        result = ranking_metrics(candidates, "absolute_error")
        self.assertEqual(result["top_n"][0]["video_id"], "b")
        self.assertEqual(result["top_n"][0]["value"], 25)

    def test_channel_model_evaluation_uses_only_paired_scores(self):
        result = model_evaluation_metrics(
            [
                {
                    "video": {"video_id": "a", "title": "A"},
                    "prediction": {"viral_score": 80},
                    "evaluation": {"label_score": 70},
                },
                {
                    "video": {"video_id": "b", "title": "B"},
                    "prediction": {"viral_score": 60},
                    "evaluation": {"label_score": 64},
                },
                {
                    "video": {"video_id": "c", "title": "C"},
                    "prediction": {"viral_score": 50},
                    "evaluation": None,
                },
            ]
        )
        self.assertEqual(result["evaluated_video_count"], 2)
        self.assertEqual(result["mean_absolute_error"]["value"], 7)

    def test_channel_baseline_uses_other_videos_median(self):
        result = baseline_comparison_metrics(
            {
                "selected_video": {"video": {"video_id": "a"}},
                "comparison_videos": [
                    {"video": {"video_id": "a"}, "prediction": {"viral_score": 80}},
                    {"video": {"video_id": "b"}, "prediction": {"viral_score": 40}},
                    {"video": {"video_id": "c"}, "prediction": {"viral_score": 60}},
                ],
            },
            "viral_score",
        )
        self.assertEqual(result["channel_median"], 50)
        self.assertEqual(result["difference"], 30)
        self.assertEqual(result["difference_rate"]["value"], 60)

    def test_data_coverage_counts_distinct_videos_not_documents(self):
        result = data_status_metrics(
            {
                "video_count": 2,
                "prediction_document_count": 10,
                "label_document_count": 10,
                "videos": [
                    {"has_prediction": True, "has_label": False, "snapshot_count": 3},
                    {"has_prediction": False, "has_label": True, "snapshot_count": 0},
                ],
            }
        )
        self.assertEqual(result["prediction_coverage"]["value"], 50)
        self.assertEqual(result["label_coverage"]["value"], 50)
        self.assertEqual(result["snapshot_coverage"]["value"], 50)


if __name__ == "__main__":
    unittest.main()
