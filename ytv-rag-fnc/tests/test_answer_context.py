"""Tests for final answer evidence metadata."""

import unittest

from shared.answer_context import build_evidence_summary


class AnswerContextTests(unittest.TestCase):
    def test_summary_tracks_sources_references_and_missing_metrics(self):
        summary = build_evidence_summary(
            {
                "data_sources": ["predictions", "videos"],
                "selected_video": {
                    "video": {"video_id": "video-a", "title": "테스트 영상"}
                },
            },
            {
                "primary_category": "prediction_score",
                "secondary_categories": ["shap_factors"],
            },
            {
                "prediction_score": {"available": True, "viral_score": 82.4},
                "shap_factors": {"available": False},
            },
            [{"id": "concept-shap", "title": "SHAP", "similarity": 0.91}],
            "embedding_cosine",
        )
        self.assertEqual(summary["selected_video"]["video_id"], "video-a")
        self.assertEqual(summary["operational_data_sources"], ["predictions", "videos"])
        self.assertIn("shap_factors", summary["unavailable_metrics"])
        self.assertEqual(summary["knowledge_references"][0]["id"], "concept-shap")


if __name__ == "__main__":
    unittest.main()
