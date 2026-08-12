import unittest
from unittest.mock import patch

from shared.question_analyzer import (
    analyze_question,
    apply_deterministic_routing,
    lexical_question_analysis,
    normalize_question_analysis,
)
from shared.question_analyzer import _fallback_channel_reference


class QuestionAnalyzerTests(unittest.TestCase):
    def test_channel_growth_uses_available_range_instead_of_clarifying(self):
        result = normalize_question_analysis(
            {
                "primary_category": "channel_growth",
                "secondary_categories": [],
                "period": None,
                "metric": None,
                "needs_clarification": True,
                "clarification_question": "어떤 기간을 볼까요?",
            }
        )
        self.assertFalse(result["needs_clarification"])
        self.assertIsNone(result["clarification_question"])

    def test_structured_result_is_normalized(self):
        result = normalize_question_analysis(
            {
                "primary_category": "shap_factors",
                "secondary_categories": ["prediction_vs_actual", "shap_factors", "unknown"],
                "channel_reference": "A 채널",
                "video_id": None,
                "video_title": "샘플 영상",
                "period": "D+3",
                "metric": "viral_score",
                "needs_clarification": False,
                "clarification_question": None,
            }
        )
        self.assertEqual(result["primary_category"], "shap_factors")
        self.assertEqual(result["secondary_categories"], ["prediction_vs_actual"])
        self.assertEqual(result["channel_reference"], "A 채널")
        self.assertEqual(result["metric"], "viral_score")

    def test_missing_clarification_text_gets_safe_default(self):
        result = normalize_question_analysis(
            {"primary_category": "video_performance", "needs_clarification": True}
        )
        self.assertTrue(result["clarification_question"])

    def test_lexical_fallback_extracts_category_period_and_metric(self):
        result = lexical_question_analysis("최근 7일 채널 성장세와 구독자 증가를 알려줘")
        self.assertEqual(result["primary_category"], "channel_growth")
        self.assertEqual(result["period"], "최근7일")
        self.assertEqual(result["metric"], "subscriber_count")
        self.assertEqual(result["source"], "lexical_fallback")

    def test_openai_failure_uses_lexical_fallback(self):
        with patch(
            "shared.question_analyzer.create_question_analysis",
            side_effect=RuntimeError("temporary failure"),
        ):
            result = analyze_question("예측이 실제로 맞았어?")
        self.assertEqual(result["primary_category"], "prediction_vs_actual")
        self.assertEqual(result["source"], "lexical_fallback")

    def test_recent_channel_performance_is_channel_growth(self):
        wrong_model_result = normalize_question_analysis(
            {
                "primary_category": "video_performance",
                "needs_clarification": True,
                "clarification_question": "어느 영상인가요?",
            }
        )
        result = apply_deterministic_routing(
            "최근 우리 성과 알려줄래?", wrong_model_result
        )
        self.assertEqual(result["primary_category"], "channel_growth")
        self.assertFalse(result["needs_clarification"])

    def test_video_list_is_a_distinct_non_clarifying_intent(self):
        result = lexical_question_analysis("내 채널이 소유하고 있는 영상들 보여줘")
        self.assertEqual(result["primary_category"], "video_list")
        self.assertFalse(result["needs_clarification"])

    def test_feature_difference_and_metric_meaning_are_glossary(self):
        questions = (
            "views_1h_log와 views_6h_log의 차이를 알려줘",
            "조회 증가 속도는 무슨 뜻이야?",
        )
        for question in questions:
            with self.subTest(question=question):
                result = lexical_question_analysis(question)
                self.assertEqual(result["primary_category"], "glossary_model")

    def test_actual_performance_ranking_does_not_require_one_video(self):
        result = lexical_question_analysis("실제 성과가 가장 좋은 영상 순위를 보여줘")
        self.assertEqual(result["primary_category"], "video_ranking")
        self.assertEqual(result["metric"], "label_score")
        self.assertFalse(result["needs_clarification"])

    def test_first_collection_vs_now_is_channel_growth(self):
        result = lexical_question_analysis("처음 수집했을 때와 지금 채널 규모를 비교해줘")
        self.assertEqual(result["primary_category"], "channel_growth")
        self.assertFalse(result["needs_clarification"])

    def test_largest_prediction_miss_is_error_ranking(self):
        result = lexical_question_analysis("예측이 가장 크게 빗나간 영상을 알려줘")
        self.assertEqual(result["primary_category"], "video_ranking")
        self.assertEqual(result["metric"], "absolute_error")
        self.assertFalse(result["needs_clarification"])

    def test_channel_wide_model_accuracy_is_not_a_single_video_question(self):
        result = lexical_question_analysis("모델이 실제 성과를 얼마나 정확하게 맞혔어?")
        self.assertEqual(result["primary_category"], "model_evaluation")
        self.assertFalse(result["needs_clarification"])

    def test_prediction_coverage_is_data_status(self):
        result = lexical_question_analysis("채널 영상 중 예측 데이터 충족률은 몇 퍼센트야?")
        self.assertEqual(result["primary_category"], "data_status")
        self.assertFalse(result["needs_clarification"])

    def test_generic_word_before_channel_is_not_a_channel_name(self):
        for question in (
            "최근 채널 성장세가 빨라지고 있는지 알려줘",
            "처음 수집했을 때와 지금 채널 규모를 비교해줘",
            "최근 7일 채널 성장세와 구독자 증가를 알려줘",
        ):
            with self.subTest(question=question):
                self.assertIsNone(_fallback_channel_reference(question))

    def test_specific_channel_name_is_still_detected_after_a_generic_mention(self):
        self.assertEqual(
            _fallback_channel_reference("우리 채널이랑 다른 채널을 비교해줘"),
            "다른",
        )

    def test_this_video_ranking_question_is_a_baseline_comparison_not_a_list(self):
        result = lexical_question_analysis("이 영상은 우리 채널에서 상위권 성과라고 볼 수 있어?")
        self.assertEqual(result["primary_category"], "channel_baseline_comparison")
        # Unlike video_ranking, this category still requires resolving a video
        # before it can be answered, so clarification stays possible.
        self.assertFalse(result["primary_category"] in {"video_ranking"})

    def test_plain_ranking_request_is_unaffected(self):
        result = lexical_question_analysis("최근 영상 중 가장 유망한 영상을 추천해줘")
        self.assertEqual(result["primary_category"], "video_ranking")

    def test_high_confidence_intent_skips_model_classifier(self):
        with patch("shared.question_analyzer.create_question_analysis") as classifier:
            result = analyze_question("영상이 뭐뭐 있는데?")
        classifier.assert_not_called()
        self.assertEqual(result["primary_category"], "video_list")
        self.assertEqual(result["source"], "deterministic_rules")

    def test_subscriber_growth_followup_is_channel_growth_without_channel_word(self):
        # No "채널/우리/내/전체" keyword, only "구독자" — used to fall through to
        # a video-required category and wrongly ask for a video id.
        result = lexical_question_analysis("구독자는 늘었는데 조회수도 같이 늘고 있어?")
        self.assertEqual(result["primary_category"], "channel_growth")
        self.assertFalse(result["needs_clarification"])

    def test_common_traits_across_top_videos_is_ranking_not_single_video(self):
        result = lexical_question_analysis("최근 점수가 높은 영상들의 공통점?")
        self.assertEqual(result["primary_category"], "video_ranking")
        self.assertFalse(result["needs_clarification"])

    def test_single_video_traits_question_is_unaffected(self):
        result = lexical_question_analysis("이 영상의 특징이 뭐야?")
        self.assertNotEqual(result["primary_category"], "video_ranking")

    def test_similar_channel_comparison_is_channel_growth_not_video_clarification(self):
        result = lexical_question_analysis("나와 비슷한 채널 중에서 나는 어느정도야?")
        self.assertEqual(result["primary_category"], "channel_growth")
        self.assertFalse(result["needs_clarification"])

    def test_other_channels_videos_is_channel_growth_despite_mentioning_video(self):
        # "영상" appears here too, but there's no single video to look up —
        # this must not silently fall through to a category that answers
        # using this channel's own videos as a stand-in for "other channels".
        result = lexical_question_analysis("다른 채널의 영상들은 어때?")
        self.assertEqual(result["primary_category"], "channel_growth")
        self.assertFalse(result["needs_clarification"])

    def test_this_video_vs_other_channel_video_is_unaffected(self):
        result = lexical_question_analysis("이 영상은 다른 채널 영상이랑 비교하면 어때?")
        self.assertNotEqual(result["primary_category"], "channel_growth")

    def test_shap_factors_for_named_video_without_shap_keyword(self):
        result = lexical_question_analysis("이 영상의 점수는 어떻게 나온거야?")
        self.assertEqual(result["primary_category"], "shap_factors")
        self.assertFalse(result["needs_clarification"])

    def test_capability_question_about_unsupported_video_type_is_glossary(self):
        result = lexical_question_analysis("쇼츠 영상도 분석할 수 있나요?")
        self.assertEqual(result["primary_category"], "glossary_model")
        self.assertFalse(result["needs_clarification"])

    def test_capability_question_naming_a_specific_video_is_unaffected(self):
        result = lexical_question_analysis("이 영상도 분석할 수 있나요?")
        self.assertNotEqual(result["primary_category"], "glossary_model")

    def test_product_identity_question_is_glossary(self):
        result = lexical_question_analysis("PredictTube는 정확히 어떤 서비스인가요?")
        self.assertEqual(result["primary_category"], "glossary_model")

    def test_score_calculation_method_question_is_glossary(self):
        result = lexical_question_analysis("바이럴 점수는 어떻게 계산되나요?")
        self.assertEqual(result["primary_category"], "glossary_model")
        self.assertFalse(result["needs_clarification"])

    def test_score_meaning_question_without_bare_viral_score_token_is_glossary(self):
        result = lexical_question_analysis("점수가 높으면 조회수가 많이 나온다는 뜻인가요?")
        self.assertEqual(result["primary_category"], "glossary_model")

    def test_score_range_question_is_glossary(self):
        result = lexical_question_analysis("바이럴 점수의 최고점과 최저점은 몇 점인가요?")
        self.assertEqual(result["primary_category"], "glossary_model")

    def test_lab_feature_question_is_glossary(self):
        result = lexical_question_analysis("실험실에 있는 저건 뭐야?")
        self.assertEqual(result["primary_category"], "glossary_model")

    def test_predicted_vs_actual_concept_question_is_glossary(self):
        result = lexical_question_analysis("예측 점수와 실제 성과는 어떻게 다른가요?")
        self.assertEqual(result["primary_category"], "glossary_model")

    def test_video_specific_score_recalculation_request_is_unaffected(self):
        result = lexical_question_analysis("이 영상 점수 계산 다시 해줘")
        self.assertNotEqual(result["primary_category"], "glossary_model")

    def test_category_average_score_is_ranking_not_single_video(self):
        result = lexical_question_analysis("같은 카테고리 평균 점수는 몇 점인가요?")
        self.assertEqual(result["primary_category"], "video_ranking")
        self.assertFalse(result["needs_clarification"])

    def test_analysis_turnaround_time_question_is_glossary(self):
        result = lexical_question_analysis("영상 분석에는 얼마나 걸리나요?")
        self.assertEqual(result["primary_category"], "glossary_model")

    def test_video_specific_turnaround_question_is_unaffected(self):
        result = lexical_question_analysis("이 영상 분석하는데 얼마나 걸려요?")
        self.assertNotEqual(result["primary_category"], "glossary_model")

    def test_data_protection_question_is_glossary(self):
        result = lexical_question_analysis("제 채널과 영상 데이터는 어떻게 저장되고 보호되나요?")
        self.assertEqual(result["primary_category"], "glossary_model")
        self.assertFalse(result["needs_clarification"])

    def test_clarification_question_scrubs_internal_field_names(self):
        result = normalize_question_analysis(
            {
                "primary_category": "prediction_score",
                "needs_clarification": True,
                "clarification_question": (
                    "어떤 점수를 말씀하시나요? (예: label_score/viral_score)"
                ),
            }
        )
        self.assertNotIn("label_score", result["clarification_question"])
        self.assertNotIn("viral_score", result["clarification_question"])


if __name__ == "__main__":
    unittest.main()
