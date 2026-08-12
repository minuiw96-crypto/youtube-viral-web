"""Tests for the global final-answer contract."""

import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from shared.answer_policy import answer_mode, answer_schema, render_answer
from shared.openai_service import create_answer


class AnswerPolicyTests(unittest.TestCase):
    def test_detailed_mode_requires_an_explicit_request(self):
        self.assertEqual(answer_mode("최근 성과 알려줘"), "brief")
        self.assertEqual(answer_mode("계산 과정과 근거를 자세히 알려줘"), "detailed")

    def test_schema_is_one_strict_shape_for_all_categories(self):
        schema = answer_schema()
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["required"], ["conclusion", "key_points", "limitation"]
        )

    def test_brief_answer_removes_markdown_translates_internal_terms_and_limits_points(self):
        output = json.dumps(
            {
                "conclusion": "## 구독자는 5.0% 증가했습니다. 불필요한 둘째 문장입니다.",
                "key_points": [
                    "- computed_metrics 기준으로 계산했습니다.",
                    "source=calculated 값입니다.",
                    "channel_snapshots 두 시점을 비교했습니다.",
                    "네 번째 근거는 나오면 안 됩니다.",
                ],
                "limitation": "evidence_summary에는 영상별 원인이 없습니다.",
            },
            ensure_ascii=False,
        )

        answer = render_answer(output, "최근 성과 알려줘")

        self.assertIn("구독자는 5.0% 증가했습니다.", answer)
        self.assertIn("계산 결과", answer)
        self.assertIn("직접 계산한 값", answer)
        self.assertIn("채널 시점별 통계", answer)
        self.assertNotIn("computed_metrics", answer)
        self.assertNotIn("source=calculated", answer)
        self.assertNotIn("channel_snapshots", answer)
        self.assertNotIn("네 번째", answer)
        self.assertNotIn("##", answer)

    def test_internal_feature_name_is_translated_even_when_user_asks_for_it(self):
        output = json.dumps(
            {
                "conclusion": "prediction_coverage는 예측값이 있는 영상의 비율입니다.",
                "key_points": [],
                "limitation": None,
            },
            ensure_ascii=False,
        )
        answer = render_answer(output, "prediction_coverage가 뭐야?")
        self.assertNotIn("prediction_coverage", answer)
        self.assertIn("예측 데이터 보유 비율", answer)

    def test_prediction_explanation_exposes_meanings_not_data_field_names(self):
        output = json.dumps(
            {
                "conclusion": "viral_score 88은 후보 영상 안에서 상대적으로 높은 점수입니다.",
                "key_points": [
                    "views_6h_log와 engagement_rate가 점수를 높이는 방향으로 작용했습니다.",
                    "duration_sec_log는 점수를 낮추는 방향으로 작용했습니다.",
                ],
                "limitation": "label_score나 실제 조회량을 보장하는 성공 확률은 아닙니다.",
            },
            ensure_ascii=False,
        )

        answer = render_answer(output, "냉면 영상의 88점은 어떤 의미야?")

        for field_name in (
            "viral_score",
            "views_6h_log",
            "engagement_rate",
            "duration_sec_log",
            "label_score",
        ):
            self.assertNotIn(field_name, answer)
        self.assertIn("바이럴 점수", answer)
        self.assertIn("게시 후 6시간 조회수 신호", answer)
        self.assertIn("참여율", answer)
        self.assertIn("영상 길이 신호", answer)

    def test_available_false_leak_is_scrubbed_regardless_of_separator(self):
        # The real context JSON always uses `"available": false` (colon), but
        # a plain-string dict entry keyed on "available=false" (equals) never
        # matched that in practice — this checks both forms are caught now.
        output = json.dumps(
            {
                "conclusion": (
                    "해당 지표가 'available: false'로 표시되어 순위를 확정할 수 없습니다."
                ),
                "key_points": [],
                "limitation": None,
            },
            ensure_ascii=False,
        )
        answer = render_answer(output, "TOP 10 순위를 알려줘")
        self.assertNotIn("available", answer)
        self.assertIn("확인할 수 없는 값", answer)

    def test_bare_container_names_and_scope_source_are_translated(self):
        output = json.dumps(
            {
                "conclusion": (
                    "채널 데이터는 videos, labels, predictions 문서로 구성되며 "
                    "scope는 authenticated_user로 기록됩니다."
                ),
                "key_points": [],
                "limitation": None,
            },
            ensure_ascii=False,
        )
        answer = render_answer(output, "데이터는 어떻게 저장되나요?")
        for internal_term in ("videos", "labels", "predictions", "authenticated_user"):
            self.assertNotIn(internal_term, answer)
        self.assertIn("영상 데이터", answer)
        self.assertIn("실제 성과 데이터", answer)
        self.assertIn("예측 데이터", answer)
        self.assertIn("로그인한 사용자", answer)

    def test_d_plus_3_substitution_does_not_duplicate_the_prefix(self):
        # The model often writes "게시 후 D+3" itself; naively substituting
        # "D+3" -> "게시 후 3일" then leaves "게시 후 게시 후 3일".
        output = json.dumps(
            {
                "conclusion": "실제 성과 라벨은 게시 후 D+3 시점에 관측된 값입니다.",
                "key_points": [],
                "limitation": None,
            },
            ensure_ascii=False,
        )
        answer = render_answer(output, "라벨은 언제 계산돼요?")
        self.assertEqual(answer.count("게시 후"), 1)
        self.assertIn("게시 후 3일 시점", answer)

    def test_unsupported_hype_is_neutralized_and_invented_cohort_is_removed(self):
        output = json.dumps(
            {
                "conclusion": "조회수 100,000회로 빠르게 확산 중인 흐름입니다.",
                "key_points": [
                    "게시 후 3일 실제 성과 점수는 84점입니다.",
                    "여름 구간 영상 중 높은 편입니다.",
                ],
                "limitation": None,
            },
            ensure_ascii=False,
        )

        answer = render_answer(output, "냉면 영상 성과를 알려줘")

        self.assertIn("조회수가 증가한 상태", answer)
        self.assertNotIn("빠르게 확산", answer)
        self.assertNotIn("여름 구간", answer)
        self.assertNotIn("높은 편", answer)

    def test_overly_precise_percentage_is_rounded_for_readability(self):
        output = json.dumps(
            {
                "conclusion": "조회수 성장률은 0.2709%입니다.",
                "key_points": ["참여율은 12.3456%입니다."],
                "limitation": None,
            },
            ensure_ascii=False,
        )

        answer = render_answer(output, "채널 성장세가 어때?")

        self.assertIn("0.3%", answer)
        self.assertIn("12.3%", answer)
        self.assertNotIn("0.2709%", answer)
        self.assertNotIn("12.3456%", answer)

    def test_key_point_that_restates_conclusion_in_different_words_is_dropped(self):
        output = json.dumps(
            {
                "conclusion": (
                    "바이럴 점수는 후보 영상 집합 안에서 모델이 예상한 상대적인 성과 점수로, "
                    "성공 확률이나 확정 조회수가 아니라 0~100 범위의 예측값입니다."
                ),
                "key_points": [
                    "바이럴 점수는 후보 영상 집합 안에서 모델이 예상한 상대 성과 점수입니다.",
                    "같은 후보군과 같은 모델 버전 안에서 비교해야 해석이 의미가 있습니다.",
                ],
                "limitation": None,
            },
            ensure_ascii=False,
        )

        answer = render_answer(output, "바이럴 점수는 무엇을 의미하나요?")

        self.assertEqual(answer.count("후보 영상 집합"), 1)
        self.assertIn("같은 모델 버전 안에서 비교", answer)

    def test_unsupported_hype_paraphrases_are_also_neutralized(self):
        output = json.dumps(
            {
                "conclusion": "이 영상은 빠르게 퍼지고 있는 흐름을 보입니다.",
                "key_points": ["폭발적으로 증가하는 추세입니다."],
                "limitation": None,
            },
            ensure_ascii=False,
        )

        answer = render_answer(output, "냉면 영상 성과를 알려줘")

        self.assertNotIn("빠르게 퍼지고", answer)
        self.assertNotIn("폭발적으로", answer)
        self.assertIn("조회수가 증가한 상태", answer)
        self.assertIn("큰 폭의 증가", answer)

    def test_create_answer_requests_structured_output_and_renders_it(self):
        api = Mock()
        api.responses.create.return_value = SimpleNamespace(
            output_text=json.dumps(
                {
                    "conclusion": "조회수는 20% 증가했습니다.",
                    "key_points": ["100만 회에서 120만 회가 됐습니다."],
                    "limitation": None,
                },
                ensure_ascii=False,
            )
        )
        with (
            patch(
                "shared.openai_service.Settings.from_environment",
                return_value=SimpleNamespace(chat_deployment="local-test"),
            ),
            patch("shared.openai_service.client", return_value=api),
        ):
            answer = create_answer("최근 성과 알려줘", "{}")

        request = api.responses.create.call_args.kwargs
        self.assertEqual(request["text"]["format"]["type"], "json_schema")
        self.assertTrue(request["text"]["format"]["strict"])
        self.assertEqual(
            answer,
            "조회수는 20% 증가했습니다.\n100만 회에서 120만 회가 됐습니다.",
        )


if __name__ == "__main__":
    unittest.main()
