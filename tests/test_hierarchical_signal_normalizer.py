import copy
import unittest

from modules.source_intake.hierarchical_signal_normalizer import (
    HIERARCHICAL_SIGNAL_NORMALIZER_VERSION,
    run_hierarchical_signal_normalizer,
)


class TestHierarchicalSignalNormalizer(unittest.TestCase):
    def test_source_topic_cohort_and_rank_direction_are_observable(self):
        candidates = [
            {
                "candidate_id": "a",
                "source_id": "community_a",
                "source_type": "community",
                "source_lane_id": "dopamine",
                "rank_position": 1,
                "visible_metrics": {"views": 100, "comments": 0},
            },
            {
                "candidate_id": "b",
                "source_id": "community_a",
                "source_type": "community",
                "source_lane_id": "dopamine",
                "rank_position": 2,
                "visible_metrics": {"views": 300, "comments": 10},
            },
        ]

        result = run_hierarchical_signal_normalizer(candidates)
        first = result["items"][0]["stage1_normalized_signals"]
        second = result["items"][1]["stage1_normalized_signals"]

        self.assertEqual(result["schema_version"], HIERARCHICAL_SIGNAL_NORMALIZER_VERSION)
        self.assertEqual(first["views"]["basis"], "source_topic")
        self.assertEqual(first["views"]["sample_size"], 2)
        self.assertLess(first["views"]["normalized_value"], second["views"]["normalized_value"])
        self.assertGreater(
            first["rank_position"]["normalized_value"],
            second["rank_position"]["normalized_value"],
        )

    def test_hierarchy_falls_back_source_then_source_type_then_batch(self):
        candidates = [
            {
                "candidate_id": "source-1",
                "source_id": "same_source",
                "source_type": "community",
                "source_lane_id": "lane_a",
                "views": 10,
            },
            {
                "candidate_id": "source-2",
                "source_id": "same_source",
                "source_type": "community",
                "source_lane_id": "lane_b",
                "views": 20,
            },
            {
                "candidate_id": "type-1",
                "source_id": "different_source",
                "source_type": "community",
                "views": 30,
            },
            {
                "candidate_id": "batch-only",
                "source_id": "news_source",
                "source_type": "news",
                "views": 40,
            },
        ]

        result = run_hierarchical_signal_normalizer(candidates)
        by_id = {item["candidate_id"]: item for item in result["items"]}

        self.assertEqual(
            by_id["source-1"]["stage1_normalized_signals"]["views"]["basis"],
            "source",
        )
        self.assertEqual(
            by_id["type-1"]["stage1_normalized_signals"]["views"]["basis"],
            "source_type",
        )
        self.assertEqual(
            by_id["batch-only"]["stage1_normalized_signals"]["views"]["basis"],
            "batch",
        )

    def test_missing_is_not_zero_and_explicit_zero_is_observed(self):
        candidates = [
            {
                "candidate_id": "news-missing",
                "source_id": "news_a",
                "source_type": "news",
                "rank_position": 1,
            },
            {
                "candidate_id": "community-zero",
                "source_id": "community_a",
                "source_type": "community",
                "visible_metrics": {"comments": 0, "likes": 0},
            },
        ]

        result = run_hierarchical_signal_normalizer(candidates)
        news = result["items"][0]["stage1_normalized_signals"]
        community = result["items"][1]["stage1_normalized_signals"]

        self.assertEqual(news["comments"]["status"], "missing")
        self.assertIsNone(news["comments"]["normalized_value"])
        self.assertEqual(news["comments"]["sample_size"], 0)
        self.assertEqual(community["comments"]["status"], "observed")
        self.assertEqual(community["comments"]["raw_value"], 0)
        self.assertEqual(community["comments"]["normalized_value"], 0.5)
        self.assertEqual(community["comments"]["basis"], "batch")

    def test_nested_and_flat_metrics_are_supported_with_nested_precedence(self):
        candidates = [
            {
                "candidate_id": "nested",
                "source_id": "source_a",
                "source_type": "community",
                "views": 999,
                "visible_metrics": {"views": 100, "comments": 2},
            },
            {
                "candidate_id": "flat",
                "source_id": "source_b",
                "source_type": "community",
                "views": 200,
                "comments": 4,
            },
        ]

        result = run_hierarchical_signal_normalizer(candidates)
        nested = result["items"][0]["stage1_normalized_signals"]
        flat = result["items"][1]["stage1_normalized_signals"]

        self.assertEqual(nested["views"]["raw_value"], 100)
        self.assertEqual(nested["views"]["value_origin"], "visible_metrics")
        self.assertEqual(flat["views"]["raw_value"], 200)
        self.assertEqual(flat["views"]["value_origin"], "flat")

    def test_ties_are_deterministic_and_input_is_not_mutated(self):
        candidates = [
            {
                "candidate_id": "a",
                "source_id": "source_a",
                "source_type": "community",
                "likes": 5,
            },
            {
                "candidate_id": "b",
                "source_id": "source_b",
                "source_type": "community",
                "likes": 5,
            },
        ]
        snapshot = copy.deepcopy(candidates)

        first = run_hierarchical_signal_normalizer(candidates)
        second = run_hierarchical_signal_normalizer(candidates)

        self.assertEqual(first, second)
        self.assertEqual(candidates, snapshot)
        self.assertEqual(
            first["items"][0]["stage1_normalized_signals"]["likes"]["normalized_value"],
            0.5,
        )
        self.assertEqual(first["items"][0]["candidate_id"], "a")

    def test_invalid_values_do_not_enter_cohorts(self):
        candidates = [
            {"source_id": "a", "source_type": "community", "views": -1},
            {"source_id": "b", "source_type": "community", "views": True},
            {"source_id": "c", "source_type": "community", "views": 50},
        ]

        result = run_hierarchical_signal_normalizer(candidates)

        self.assertEqual(
            result["items"][0]["stage1_normalized_signals"]["views"]["status"],
            "invalid",
        )
        self.assertEqual(
            result["items"][1]["stage1_normalized_signals"]["views"]["status"],
            "invalid",
        )
        observed = result["items"][2]["stage1_normalized_signals"]["views"]
        self.assertEqual(observed["sample_size"], 1)
        self.assertEqual(observed["normalized_value"], 0.5)

    def test_malformed_top_level_or_member_fails_closed(self):
        for malformed in (None, {}, "not-a-list", ["not-an-object"]):
            result = run_hierarchical_signal_normalizer(malformed)
            self.assertEqual(result["status"], "closed")
            self.assertEqual(result["items"], [])
            self.assertEqual(result["item_count"], 0)


if __name__ == "__main__":
    unittest.main()
