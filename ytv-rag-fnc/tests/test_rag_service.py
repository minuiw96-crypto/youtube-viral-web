import unittest
from types import SimpleNamespace
from unittest.mock import patch

from shared.rag_service import ChannelAccessError, RagService, _match_video


class FakeRepository:
    def get_channel(self, channel_id):
        if channel_id != "channel-a":
            return None
        return {"channel_id": channel_id, "channel_title": "테스트 채널"}

    def get_channel_snapshots(self, channel_id, limit=100):
        return []

    def list_channel_videos(self, channel_id, limit=50):
        return [self.get_video("video-a")]

    def get_video(self, video_id):
        return {
            "id": video_id,
            "video_id": video_id,
            "channel_id": "channel-a" if video_id == "video-a" else "channel-b",
            "title": "테스트 영상",
        }

    def get_latest_prediction(self, video_id):
        return {"video_id": video_id, "predicted_score": 82.4}

    def get_snapshots(self, video_id):
        return [{"video_id": video_id, "view_count": 1000, "target_age_hours": 24}]

    def get_evaluation(self, video_id, candidate_batch_id):
        return {"video_id": video_id, "label_score": 76.0, "target_horizon": "D+3"}


class TrackingRepository(FakeRepository):
    def __init__(self):
        self.calls = []

    def get_channel(self, channel_id):
        self.calls.append("channels")
        return super().get_channel(channel_id)

    def get_channel_snapshots(self, channel_id, limit=100):
        self.calls.append("channel_snapshots")
        return [{"channel_id": channel_id, "subscriber_count": 100}]

    def list_channel_videos(self, channel_id, limit=50):
        self.calls.append("videos")
        return [super().get_video("video-a")]

    def get_video(self, video_id):
        self.calls.append("selected_video")
        return super().get_video(video_id)

    def get_latest_prediction(self, video_id):
        self.calls.append("selected_prediction")
        return super().get_latest_prediction(video_id)

    def get_snapshots(self, video_id, limit=100):
        self.calls.append("selected_snapshots")
        return super().get_snapshots(video_id)

    def get_evaluation(self, video_id, candidate_batch_id):
        self.calls.append("selected_evaluation")
        return super().get_evaluation(video_id, candidate_batch_id)

    def list_channel_predictions(self, channel_id, limit=100):
        self.calls.append("channel_predictions")
        return [
            {
                "video_id": "video-a",
                "channel_id": channel_id,
                "predicted_score": 82.4,
                "predicted_at": "2026-08-01T00:00:00Z",
            }
        ]

    def list_channel_labels(self, channel_id, limit=100):
        self.calls.append("channel_labels")
        return [
            {
                "video_id": "video-a",
                "channel_id": channel_id,
                "label_score": 76.0,
                "calculated_at": "2026-08-04T00:00:00Z",
            }
        ]

    def list_channel_video_snapshots(self, channel_id, limit=300):
        self.calls.append("channel_video_snapshots")
        return [
            {
                "video_id": "video-a",
                "channel_id": channel_id,
                "view_count": 1000,
                "snapshot_time": "2026-08-02T00:00:00Z",
            }
        ]


class RagScopeTests(unittest.TestCase):
    def test_video_in_channel_is_available(self):
        service = RagService(repository=FakeRepository())
        context = service._video_context("video-a", "channel-a")
        self.assertEqual(context["video"]["channel_id"], "channel-a")
        self.assertEqual(context["prediction"]["viral_score"], 82.4)

    def test_video_from_other_channel_is_rejected(self):
        service = RagService(repository=FakeRepository())
        with self.assertRaises(ChannelAccessError) as forbidden:
            service._video_context("video-b", "channel-a")
        self.assertEqual(forbidden.exception.code, "CHANNEL_FORBIDDEN")

    def test_user_scope_comes_from_authenticated_user(self):
        service = RagService(repository=FakeRepository())
        channel_id, source = service.resolve_channel_scope(
            {"channel_id": "channel-b"},
            {"role": "user", "channel_id": "channel-a"},
        )
        self.assertEqual(channel_id, "channel-a")
        self.assertEqual(source, "authenticated_user")

    def test_explicit_other_channel_in_question_is_rejected(self):
        service = RagService(repository=FakeRepository())
        with self.assertRaises(ChannelAccessError) as forbidden:
            service.enforce_question_scope(
                {"channel_reference": "다른 채널"},
                {
                    "role": "user",
                    "channel_id": "channel-a",
                    "channel_title": "테스트 채널",
                },
                "channel-a",
                "다른 채널의 조회수도 알려줘",
            )
        self.assertEqual(forbidden.exception.code, "CHANNEL_FORBIDDEN")

    def test_own_channel_title_in_question_is_allowed(self):
        service = RagService(repository=FakeRepository())
        service.enforce_question_scope(
            {"channel_reference": "테스트 채널"},
            {
                "role": "user",
                "channel_id": "channel-a",
                "channel_title": "테스트 채널",
            },
            "channel-a",
            "테스트 채널의 성과를 알려줘",
        )

    def test_video_id_misclassified_as_channel_reference_is_not_rejected(self):
        service = RagService(repository=FakeRepository())
        service.enforce_question_scope(
            {"channel_reference": "video-a"},
            {
                "role": "user",
                "channel_id": "channel-a",
                "channel_title": "테스트 채널",
            },
            "channel-a",
            "video-a 영상 점수를 알려줘",
        )

    def test_explicit_other_uc_channel_id_is_rejected_without_model_extraction(self):
        service = RagService(repository=FakeRepository())
        with self.assertRaises(ChannelAccessError) as forbidden:
            service.enforce_question_scope(
                {"channel_reference": None},
                {
                    "role": "user",
                    "channel_id": "UC_ALLOWED_001",
                    "channel_title": "테스트 채널",
                },
                "UC_ALLOWED_001",
                "UC_FORBIDDEN_002 채널도 비교해줘",
            )
        self.assertEqual(forbidden.exception.code, "CHANNEL_FORBIDDEN")

    def test_user_without_channel_is_rejected(self):
        service = RagService(repository=FakeRepository())
        with self.assertRaises(ChannelAccessError) as missing:
            service.resolve_channel_scope({}, {"role": "user", "channel_id": None})
        self.assertEqual(missing.exception.code, "CHANNEL_NOT_ASSIGNED")

    def test_admin_can_select_an_existing_channel(self):
        service = RagService(repository=FakeRepository())
        channel_id, source = service.resolve_channel_scope(
            {"channel_id": "channel-a"},
            {"role": "admin", "channel_id": None},
        )
        self.assertEqual(channel_id, "channel-a")
        self.assertEqual(source, "admin_selected")

    def test_admin_cannot_select_an_unknown_channel(self):
        service = RagService(repository=FakeRepository())
        with self.assertRaises(ChannelAccessError) as missing:
            service.resolve_channel_scope(
                {"channel_id": "missing-channel"},
                {"role": "admin", "channel_id": None},
            )
        self.assertEqual(missing.exception.code, "CHANNEL_NOT_FOUND")

    def test_generic_word_before_channel_does_not_trigger_a_false_block(self):
        service = RagService(repository=FakeRepository())
        # Regression: "최근 채널 성장세가..." used to misread "최근" as an
        # explicit reference to a different channel and raise here.
        service.enforce_question_scope(
            {"channel_reference": "최근"},
            {
                "role": "user",
                "channel_id": "channel-a",
                "channel_title": "테스트 채널",
            },
            "channel-a",
            "최근 채널 성장세가 빨라지고 있는지 알려줘",
        )


class CategoryRoutingTests(unittest.TestCase):
    def _context(self, category, selected_video_id=None, question="질문"):
        repository = TrackingRepository()
        service = RagService(repository=repository)
        context = service._channel_context(
            "channel-a",
            selected_video_id,
            question,
            {
                "primary_category": category,
                "secondary_categories": [],
            },
        )
        return context, repository.calls

    def test_channel_growth_reads_only_channel_growth_sources(self):
        context, calls = self._context("channel_growth", question="우리 채널 성장세")
        self.assertEqual(
            context["data_sources"],
            ["channel_snapshots", "channels", "videos"],
        )
        self.assertNotIn("channel_predictions", calls)
        self.assertNotIn("channel_labels", calls)
        self.assertNotIn("channel_video_snapshots", calls)

    def test_video_list_reads_videos_without_clarification(self):
        context, calls = self._context("video_list", question="영상이 뭐뭐 있는데?")
        self.assertEqual(context["data_sources"], ["videos"])
        self.assertEqual(context["video_count_in_context"], 1)
        self.assertFalse(context["needs_clarification"])
        self.assertEqual(calls, ["videos"])

    def test_video_performance_reads_selected_video_and_snapshots_only(self):
        context, calls = self._context("video_performance", "video-a")
        self.assertEqual(context["data_sources"], ["video_snapshots", "videos"])
        self.assertIn("selected_video", calls)
        self.assertIn("selected_snapshots", calls)
        self.assertNotIn("selected_prediction", calls)
        self.assertNotIn("selected_evaluation", calls)

    def test_prediction_vs_actual_reads_prediction_snapshots_and_label(self):
        context, calls = self._context("prediction_vs_actual", "video-a")
        self.assertEqual(
            context["data_sources"],
            ["labels", "predictions", "video_snapshots", "videos"],
        )
        self.assertIn("selected_prediction", calls)
        self.assertIn("selected_snapshots", calls)
        self.assertIn("selected_evaluation", calls)

    def test_missing_video_returns_clarification_before_detail_queries(self):
        context, calls = self._context("shap_factors", question="왜 점수가 높아?")
        self.assertTrue(context["needs_clarification"])
        self.assertTrue(context["available_videos"])
        self.assertNotIn("selected_prediction", calls)

    def test_glossary_question_skips_operational_cosmos_queries(self):
        context, calls = self._context("glossary_model", question="SHAP이 뭐야?")
        self.assertEqual(context["data_sources"], [])
        self.assertEqual(calls, [])

    def test_data_status_uses_channel_batch_queries(self):
        context, calls = self._context("data_status", question="왜 실제 점수가 없어?")
        self.assertIn("channel_predictions", calls)
        self.assertIn("channel_labels", calls)
        self.assertIn("channel_video_snapshots", calls)
        self.assertEqual(context["data_status"]["video_count"], 1)
        self.assertTrue(context["data_status"]["videos"][0]["has_prediction"])

    def test_model_evaluation_uses_channel_batches_without_selecting_one_video(self):
        context, calls = self._context(
            "model_evaluation", question="모델이 얼마나 정확하게 맞혔어?"
        )
        self.assertFalse(context["needs_clarification"])
        self.assertIn("channel_predictions", calls)
        self.assertIn("channel_labels", calls)
        self.assertNotIn("selected_video", calls)


class EmbeddingRagTests(unittest.TestCase):
    def test_embedding_search_is_used_when_documents_exist(self):
        repository = FakeRepository()
        repository.vector_search = lambda embedding, channel_id: [
            {"id": "concept-shap", "title": "SHAP", "similarity": 0.91}
        ]
        service = RagService(repository=repository)
        service.settings = SimpleNamespace(vector_search_ready=True)
        with patch("shared.rag_service.create_embedding", return_value=[0.1, 0.2]):
            documents, mode = service._knowledge("SHAP이 뭐야?", "channel-a")
        self.assertEqual(mode, "embedding_cosine")
        self.assertEqual(documents[0]["id"], "concept-shap")

    def test_empty_embedding_index_uses_lexical_fallback(self):
        repository = FakeRepository()
        repository.vector_search = lambda embedding, channel_id: []
        service = RagService(repository=repository)
        service.settings = SimpleNamespace(vector_search_ready=True)
        with patch("shared.rag_service.create_embedding", return_value=[0.1, 0.2]):
            documents, mode = service._knowledge("참여율이 뭐야?", "channel-a")
        self.assertEqual(mode, "built_in_lexical")
        self.assertTrue(documents)

    def test_indexing_embeds_in_one_batch_and_upserts_every_document(self):
        stored = []
        repository = FakeRepository()
        repository.upsert_rag_document = lambda document: stored.append(document) or document
        service = RagService(repository=repository)
        service.settings = SimpleNamespace(
            vector_search_ready=True,
            embedding_deployment="ytv-text-embedding",
        )

        def fake_embeddings(texts):
            return [[float(index), 1.0] for index, _ in enumerate(texts)]

        with patch("shared.rag_service.create_embeddings", side_effect=fake_embeddings) as mocked:
            result = service.index_seed_knowledge()
        mocked.assert_called_once()
        self.assertEqual(result["indexed_count"], len(stored))
        self.assertEqual(result["embedding_dimensions"], 2)
        self.assertTrue(all(row["embedding_model"] == "ytv-text-embedding" for row in stored))


class FinalAnswerPipelineTests(unittest.TestCase):
    def test_all_categories_reach_final_answer_with_auditable_context(self):
        categories = [
            "channel_growth",
            "video_list",
            "video_performance",
            "prediction_score",
            "shap_factors",
            "prediction_vs_actual",
            "video_ranking",
            "channel_baseline_comparison",
            "data_status",
            "glossary_model",
        ]
        video_categories = {
            "video_performance",
            "prediction_score",
            "shap_factors",
            "prediction_vs_actual",
            "channel_baseline_comparison",
        }

        for category in categories:
            with self.subTest(category=category):
                service = RagService(repository=TrackingRepository())
                service.settings = SimpleNamespace(
                    cosmos_ready=True,
                    vector_search_ready=False,
                )
                analysis = {
                    "primary_category": category,
                    "secondary_categories": [],
                    "channel_reference": None,
                    "video_id": None,
                    "video_title": None,
                    "period": None,
                    "metric": None,
                    "needs_clarification": False,
                    "clarification_question": None,
                }
                body = {"question": "테스트 질문"}
                if category in video_categories:
                    body["video_id"] = "video-a"

                with (
                    patch("shared.rag_service.analyze_question", return_value=analysis),
                    patch(
                        "shared.rag_service.create_answer",
                        return_value="검증된 최종 답변",
                    ) as answer_mock,
                ):
                    result = service.answer(
                        body,
                        {"role": "user", "channel_id": "channel-a"},
                    )

                self.assertEqual(result["answer"], "검증된 최종 답변")
                self.assertEqual(
                    result["evidence_summary"]["primary_category"], category
                )
                self.assertEqual(result["personalization"]["channel_id"], "channel-a")
                context_json = answer_mock.call_args.args[1]
                self.assertIn('"response_contract"', context_json)
                self.assertIn('"evidence_summary"', context_json)
                self.assertNotIn("contentVector", context_json)


class VideoIdentificationTests(unittest.TestCase):
    def setUp(self):
        self.videos = [
            {"video_id": "DEMO_A_001", "title": "여름엔 역시 냉면 먹방"},
            {"video_id": "DEMO_A_002", "title": "매운 떡볶이 도전"},
            {"video_id": "DEMO_A_003", "title": "편의점 신상 디저트 리뷰"},
        ]

    def test_exact_id_and_title_are_resolved(self):
        self.assertEqual(_match_video("DEMO_A_001", self.videos), "DEMO_A_001")
        self.assertEqual(
            _match_video("여름엔 역시 냉면 먹방 영상의 SHAP 값을 알려줘", self.videos),
            "DEMO_A_001",
        )

    def test_unique_partial_title_is_resolved(self):
        self.assertEqual(_match_video("냉면 영상", self.videos), "DEMO_A_001")
        self.assertEqual(
            _match_video("편의점 신상 테스트 영상 SHAP 값", self.videos),
            "DEMO_A_003",
        )

    def test_digit_korean_spacing_mismatch_still_resolves(self):
        videos = self.videos + [
            {"video_id": "DEMO_A_004", "title": "연평도 1편 대게 먹방"}
        ]
        self.assertEqual(_match_video("연평도1편 영상", videos), "DEMO_A_004")

    def test_ambiguous_generic_reference_is_not_guessed(self):
        self.assertIsNone(_match_video("이 영상 조회수", self.videos))

    def test_service_resolves_title_before_honoring_model_clarification(self):
        service = RagService(repository=TrackingRepository())
        service.settings = SimpleNamespace(cosmos_ready=True, vector_search_ready=False)
        analysis = {
            "primary_category": "video_performance",
            "secondary_categories": [],
            "channel_reference": None,
            "video_id": None,
            "video_title": "테스트 영상",
            "period": None,
            "metric": "view_count",
            "needs_clarification": True,
            "clarification_question": "어느 영상인가요?",
        }
        with (
            patch("shared.rag_service.analyze_question", return_value=analysis),
            patch("shared.rag_service.create_answer", return_value="정상 답변"),
        ):
            result = service.answer(
                {"question": "테스트 영상 조회수 알려줘"},
                {"role": "user", "channel_id": "channel-a"},
            )
        self.assertEqual(result["answer"], "정상 답변")
        self.assertEqual(result["selected_video_id"], "video-a")

    def test_own_video_id_is_authorized_even_if_model_calls_it_a_channel(self):
        service = RagService(repository=TrackingRepository())
        service.settings = SimpleNamespace(cosmos_ready=True, vector_search_ready=False)
        analysis = {
            "primary_category": "prediction_score",
            "secondary_categories": [],
            "channel_reference": "video-a",
            "video_id": "video-a",
            "video_title": None,
            "period": None,
            "metric": "viral_score",
            "needs_clarification": False,
            "clarification_question": None,
        }
        with (
            patch("shared.rag_service.analyze_question", return_value=analysis),
            patch("shared.rag_service.create_answer", return_value="허용된 답변"),
        ):
            result = service.answer(
                {"question": "video-a 점수를 알려줘"},
                {
                    "role": "user",
                    "channel_id": "channel-a",
                    "channel_title": "테스트 채널",
                },
            )
        self.assertEqual(result["answer"], "허용된 답변")
        self.assertEqual(result["selected_video_id"], "video-a")

    def test_other_channel_video_is_still_rejected_by_stored_channel_id(self):
        service = RagService(repository=TrackingRepository())
        service.settings = SimpleNamespace(cosmos_ready=True, vector_search_ready=False)
        analysis = {
            "primary_category": "prediction_score",
            "secondary_categories": [],
            "channel_reference": "video-b",
            "video_id": "video-b",
            "video_title": None,
            "period": None,
            "metric": "viral_score",
            "needs_clarification": False,
            "clarification_question": None,
        }
        with patch("shared.rag_service.analyze_question", return_value=analysis):
            with self.assertRaises(ChannelAccessError) as forbidden:
                service.answer(
                    {"question": "video-b 점수를 알려줘"},
                    {
                        "role": "user",
                        "channel_id": "channel-a",
                        "channel_title": "테스트 채널",
                    },
                )
        self.assertEqual(forbidden.exception.code, "CHANNEL_FORBIDDEN")

    def test_follow_up_reference_uses_conversation_video(self):
        service = RagService(repository=TrackingRepository())
        service.settings = SimpleNamespace(cosmos_ready=True, vector_search_ready=False)
        analysis = {
            "primary_category": "channel_baseline_comparison",
            "secondary_categories": [],
            "channel_reference": None,
            "video_id": None,
            "video_title": None,
            "period": None,
            "metric": "viral_score",
            "needs_clarification": True,
            "clarification_question": "어느 영상인가요?",
        }
        with (
            patch("shared.rag_service.analyze_question", return_value=analysis),
            patch("shared.rag_service.create_answer", return_value="이어진 답변"),
        ):
            result = service.answer(
                {
                    "question": "구독자 규모를 고려해도 이 영상이 잘된 편이야?",
                    "context_video_id": "video-a",
                },
                {"role": "user", "channel_id": "channel-a"},
            )
        self.assertEqual(result["answer"], "이어진 답변")
        self.assertEqual(result["selected_video_id"], "video-a")


if __name__ == "__main__":
    unittest.main()
