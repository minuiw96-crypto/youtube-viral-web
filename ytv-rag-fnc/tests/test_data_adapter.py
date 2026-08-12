import unittest

from shared.data_adapter import (
    normalize_evaluation,
    normalize_prediction,
    normalize_snapshot,
    normalize_video,
)


class DataAdapterTests(unittest.TestCase):
    def test_current_prediction_is_normalized(self):
        result = normalize_prediction(
            {
                "video_id": "mukbang_015",
                "model_version": "baseline-v1",
                "raw_prediction": 1.528,
                "expected_performance_multiplier": 1.528,
                "viral_score": 68.8,
                "rank": 1,
                "candidate_count": 17,
                "top_positive_factors": ["season_match_score"],
                "top_negative_factors": ["same_food_upload_count_24h"],
            }
        )
        self.assertEqual(result["viral_score"], 68.8)
        self.assertEqual(result["rank"], 1)
        self.assertFalse(result["explanation"]["has_numeric_impacts"])
        self.assertEqual(
            result["explanation"]["positive_factors"], ["season_match_score"]
        )

    def test_rich_output_keeps_time_horizons_and_explanation_method(self):
        result = normalize_prediction(
            {
                "video_id": "mukbang_015",
                "prediction": {
                    "viral_score": 68.8,
                    "expected_relative_performance": 1.528,
                    "estimated_7d_views": 1356440,
                    "baseline_7d_views": 887959,
                },
                "input_features": {"season_match_score": 1.0},
                "local_explanation": {
                    "method": "synthetic_shap_like",
                    "values": [
                        {
                            "feature": "season_match_score",
                            "value": 1.0,
                            "impact": 0.1,
                            "direction": "positive",
                        }
                    ],
                },
            }
        )
        self.assertEqual(result["estimated_7d_views"], 1356440)
        self.assertIsNone(result["estimated_72h_views"])
        self.assertEqual(result["explanation"]["method"], "synthetic_shap_like")
        self.assertTrue(result["explanation"]["has_numeric_impacts"])

    def test_latest_schema_is_normalized(self):
        video = normalize_video(
            {
                "id": "video_1",
                "channel_id": "UCxxxx",
                "system": {"project_category": "kr_mukbang"},
                "youtube_raw": {
                    "snippet": {"title": "냉면 먹방", "published_at": "2026-08-04Z"}
                },
            }
        )
        prediction = normalize_prediction(
            {
                "video_id": "video_1",
                "predicted_score": 82.4,
                "model_name": "youtube-viral-xgb",
                "model_version": "v1",
            }
        )
        snapshot = normalize_snapshot(
            {
                "video_id": "video_1",
                "snapshot_time": "2026-08-04T00:30:00Z",
                "view_count": 1250,
            }
        )
        label = normalize_evaluation(
            {
                "video_id": "video_1",
                "label_score": 78.4,
                "target_horizon": "D+3",
                "calculated_at": "2026-08-07T00:00:00Z",
            }
        )
        self.assertEqual(video["channel_id"], "UCxxxx")
        self.assertEqual(video["title"], "냉면 먹방")
        self.assertEqual(prediction["viral_score"], 82.4)
        self.assertEqual(snapshot["collected_at"], "2026-08-04T00:30:00Z")
        self.assertEqual(label["target_horizon"], "D+3")


if __name__ == "__main__":
    unittest.main()
