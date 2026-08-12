"""Tests for the small-corpus embedding search implementation."""

import unittest

from shared.embedding_search import cosine_similarity, rank_documents
from shared.knowledge_base import embedding_text, lexical_search, seed_documents
from shared.search_normalization import normalize_search_text, search_tokens


class EmbeddingSearchTests(unittest.TestCase):
    def test_cosine_similarity(self):
        self.assertEqual(cosine_similarity([1, 0], [1, 0]), 1)
        self.assertEqual(cosine_similarity([1, 0], [0, 1]), 0)
        self.assertIsNone(cosine_similarity([1], [1, 0]))
        self.assertIsNone(cosine_similarity([0, 0], [1, 0]))

    def test_documents_are_ranked_and_vectors_are_not_exposed(self):
        result = rank_documents(
            [1, 0],
            [
                {
                    "id": "less-relevant",
                    "contentVector": [0, 1],
                    "content": "less",
                },
                {
                    "id": "relevant",
                    "contentVector": [0.9, 0.1],
                    "content": "relevant",
                },
            ],
            limit=1,
        )
        self.assertEqual(result[0]["id"], "relevant")
        self.assertNotIn("contentVector", result[0])
        self.assertGreater(result[0]["similarity"], 0.9)

    def test_bad_vectors_are_skipped(self):
        result = rank_documents(
            [1, 0],
            [
                {"id": "missing"},
                {"id": "wrong-size", "contentVector": [1]},
                {"id": "valid", "contentVector": [1, 0]},
            ],
        )
        self.assertEqual([row["id"] for row in result], ["valid"])

    def test_seed_documents_include_search_terms_and_version(self):
        documents = seed_documents()
        self.assertGreaterEqual(len(documents), 20)
        self.assertTrue(all(row["channel_id"] == "GLOBAL" for row in documents))
        self.assertTrue(all(row["knowledge_version"] == "2.4.0" for row in documents))
        shap = next(row for row in documents if row["id"] == "concept-shap")
        text = embedding_text(shap)
        self.assertIn("SHAP", text)
        self.assertIn("관련 용어", text)

    def test_search_normalizes_feature_name_separators_and_case(self):
        variants = ["views_1h_log", "VIEWS-1H-LOG", "views 1h log"]
        for query in variants:
            with self.subTest(query=query):
                self.assertEqual(
                    lexical_search(f"{query}가 뭐야?", limit=1)[0]["id"],
                    "feature-views-1h-log",
                )

    def test_search_matches_korean_spacing_and_particles(self):
        self.assertEqual(
            lexical_search("조회증가속도는 무슨 뜻이야?", limit=1)[0]["id"],
            "metric-view-velocity",
        )
        self.assertIn("참여율", search_tokens("참여율이 어떻게 계산돼?"))

    def test_search_returns_both_explicitly_compared_features(self):
        result = lexical_search("views_1h_log와 views_6h_log의 차이를 알려줘")
        ids = {document["id"] for document in result}
        self.assertEqual(
            ids,
            {"feature-views-1h-log", "feature-views-6h-log"},
        )

    def test_search_does_not_return_unrelated_default_documents(self):
        self.assertEqual(lexical_search("완전히무관한표현입니다"), [])

    def test_unicode_is_normalized(self):
        self.assertEqual(normalize_search_text("ＶＩＥＷＳ＿１Ｈ＿ＬＯＧ"), "views 1h log")


if __name__ == "__main__":
    unittest.main()
