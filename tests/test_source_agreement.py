import copy
import unittest

from modules.source_intake.source_agreement import build_source_agreement


class TestSourceAgreement(unittest.TestCase):
    def test_url_cluster_uses_canonical_link_without_fragment_and_with_sorted_query(self):
        items = [
            {
                "source_id": "s1",
                "title": "뉴스A",
                "link": "https://example.com/article?a=1&b=2#sec",
            },
            {
                "source_id": "s2",
                "title": "뉴스B",
                "link": "https://example.com/article?b=2&a=1&utm_source=news",
            },
            {
                "source_id": "s3",
                "title": "완전다른 제목",
                "link": "https://example.com/other",
            },
        ]

        result = build_source_agreement(items, min_distinct_sources=2)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["summary"]["total_clusters"], 2)
        first = result["clusters"][0]
        self.assertEqual(first["member_indexes"], [0, 1])
        self.assertEqual(first["agreement_status"], "agreed")
        self.assertEqual(first["distinct_source_count"], 2)
        self.assertEqual(first["source_ids"], ["s1", "s2"])

    def test_title_similarity_cluster_by_similarity_threshold_boundary(self):
        items = [
            {"source_id": "s1", "title": "alpha beta gamma", "link": ""},
            {"source_id": "s2", "title": "alpha beta delta", "link": ""},
            {"source_id": "s3", "title": "unrelated topic", "link": "https://example.com/3"},
        ]

        result = build_source_agreement(items, min_distinct_sources=2, title_similarity_threshold=0.5)
        first_cluster = result["clusters"][0]
        self.assertEqual(first_cluster["member_indexes"], [0, 1])
        self.assertEqual(first_cluster["agreement_status"], "agreed")
        self.assertEqual(first_cluster["distinct_source_count"], 2)

    def test_same_source_duplicates_do_not_create_agreement(self):
        items = [
            {
                "source_id": "s1",
                "title": "동일한 제목",
                "link": "https://example.com/post?u=1",
            },
            {
                "source_id": "s1",
                "title": "동일한 제목",
                "link": "https://example.com/post?u=2",
            },
            {
                "source_id": "s2",
                "title": "동일한 제목",
                "link": "https://example.com/post?u=3",
            },
        ]

        result = build_source_agreement(items, min_distinct_sources=2)

        first = result["clusters"][0]
        self.assertEqual(first["agreement_status"], "agreed")
        self.assertEqual(first["source_ids"], ["s1", "s2"])
        self.assertEqual(first["distinct_source_count"], 2)

        self.assertEqual(result["summary"]["agreed_clusters"], 1)
        self.assertEqual(result["summary"]["agreed_items"], 3)

    def test_rejects_malformed_input_without_exceptions_and_marks_unattributed_rows(self):
        items = [
            "bad-item",
            {"title": "제목없음", "link": "https://example.com/ok"},
            {"source_id": "", "title": "", "link": ""},
            {"source_id": "s2", "title": "제목2", "link": "https://example.com/ok2"},
        ]

        result = build_source_agreement(items)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["summary"]["total_clusters"], 4)
        rows = result["clusters"]
        self.assertEqual(rows[1]["member_indexes"], [1])
        self.assertEqual(rows[1]["agreement_status"], "single_source")
        self.assertEqual(rows[1]["source_ids"], [])

    def test_deterministic_order_preserves_first_occurrence_representative(self):
        items = [
            {"source_id": "s2", "title": "B title", "link": "https://example.com/b"},
            {"source_id": "s1", "title": "A title", "link": "https://example.com/a"},
            {"source_id": "s3", "title": "A title", "link": "https://example.com/a?x=1"},
        ]

        result = build_source_agreement(items, title_similarity_threshold=1.0)

        self.assertEqual(result["clusters"][0]["representative_index"], 0)
        self.assertEqual(result["clusters"][1]["representative_index"], 1)
        self.assertEqual(result["clusters"][1]["member_indexes"], [1, 2])

    def test_threshold_boundary_is_honored(self):
        items = [
            {"source_id": "s1", "title": "a b c d", "link": ""},
            {"source_id": "s2", "title": "a b e f g", "link": ""},
            {"source_id": "s3", "title": "x y z", "link": ""},
        ]

        result = build_source_agreement(items, title_similarity_threshold=0.28)
        first = result["clusters"][0]
        self.assertEqual(first["member_indexes"], [0, 1])
        self.assertEqual(first["distinct_source_count"], 2)
        second = result["clusters"][1]
        self.assertEqual(second["member_indexes"], [2])

        boundary = build_source_agreement(items, title_similarity_threshold=0.29)
        self.assertEqual(boundary["clusters"][0]["member_indexes"], [0])

    def test_immutability_of_input(self):
        items = [
            {"source_id": "s1", "title": "immutable", "link": "https://example.com/1"},
            {"source_id": "s2", "title": "immutable", "link": "https://example.com/2"},
        ]
        snapshot = copy.deepcopy(items)

        build_source_agreement(items)
        self.assertEqual(items, snapshot)

    def test_empty_input_returns_closed_with_zero_counts(self):
        result = build_source_agreement([])
        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["summary"]["total_clusters"], 0)
        self.assertEqual(result["clusters"], [])


if __name__ == "__main__":
    unittest.main()
