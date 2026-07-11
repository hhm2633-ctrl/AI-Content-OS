import unittest

from modules.competitor_learning.competitor_learning_score import CompetitorLearningScorer


def _stats(**overrides):
    base = {
        "hook_statistics": {
            "sample_size": 10,
            "top": [{"value": "attention", "count": 6, "avg_likes": 100, "avg_comments": 10, "avg_confidence": 0.6}],
        },
        "cta_statistics": {
            "sample_size": 10,
            "top": [{"value": "save", "count": 5, "avg_likes": 80, "avg_comments": 8, "avg_confidence": 0.5}],
        },
        "pattern_statistics": {
            "sample_size": 10,
            "top": [{"value": "number_list", "count": 4, "avg_likes": 50, "avg_comments": 5, "avg_confidence": 0.4}],
        },
        "layout_statistics": {
            "sample_size": 10,
            "top_layouts": [{"value": "carousel", "count": 7, "avg_likes": 120, "avg_comments": 12}],
        },
    }
    base.update(overrides)
    return base


class TestCompetitorLearningScorer(unittest.TestCase):
    def setUp(self):
        self.scorer = CompetitorLearningScorer()

    def test_build_entries_empty_statistics_returns_empty_list(self):
        self.assertEqual(self.scorer.build_entries({}), [])

    def test_build_entries_none_statistics_does_not_raise(self):
        self.assertEqual(self.scorer.build_entries(None), [])

    def test_build_entries_skips_unknown_values(self):
        stats = _stats(hook_statistics={"sample_size": 5, "top": [{"value": "unknown", "count": 5}]})
        entries = self.scorer.build_entries(stats)
        self.assertFalse(any(e["type"] == "hook" for e in entries))

    def test_build_entries_includes_hook_cta_pattern_layout_types(self):
        entries = self.scorer.build_entries(_stats())
        types = {entry["type"] for entry in entries}
        self.assertEqual(types, {"hook", "cta", "pattern", "layout"})

    def test_build_entries_overall_score_within_valid_range(self):
        entries = self.scorer.build_entries(_stats())
        for entry in entries:
            score = entry["score"]["overall_score"]
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_build_entries_ranked_by_score_descending(self):
        entries = self.scorer.build_entries(_stats())
        scores = [entry["score"]["overall_score"] for entry in entries]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_build_entries_rank_field_assigned_sequentially(self):
        entries = self.scorer.build_entries(_stats())
        ranks = [entry["rank"] for entry in entries]
        self.assertEqual(ranks, list(range(1, len(entries) + 1)))

    def test_build_entries_layout_has_zero_confidence_component(self):
        entries = self.scorer.build_entries(_stats())
        layout_entry = next(e for e in entries if e["type"] == "layout")
        self.assertEqual(layout_entry["score"]["confidence"], 0.0)

    def test_build_entries_engagement_factor_zero_when_no_likes_observed(self):
        stats = _stats(
            hook_statistics={"sample_size": 5, "top": [{"value": "attention", "count": 5, "avg_likes": None}]},
            cta_statistics={"sample_size": 0, "top": []},
            pattern_statistics={"sample_size": 0, "top": []},
            layout_statistics={"sample_size": 0, "top_layouts": []},
        )
        entries = self.scorer.build_entries(stats)
        self.assertEqual(entries[0]["score"]["engagement_factor"], 0.0)

    def test_build_entries_knowledge_id_format(self):
        entries = self.scorer.build_entries(_stats())
        hook_entry = next(e for e in entries if e["type"] == "hook")
        self.assertEqual(hook_entry["knowledge_id"], "competitor_learning_hook_attention")

    def test_build_entries_never_raises_on_malformed_statistics(self):
        malformed = {"hook_statistics": "not_a_dict", "cta_statistics": None}
        entries = self.scorer.build_entries(malformed)
        self.assertEqual(entries, [])

    def test_build_entries_share_computed_from_sample_size(self):
        entries = self.scorer.build_entries(_stats())
        hook_entry = next(e for e in entries if e["type"] == "hook")
        self.assertEqual(hook_entry["score"]["share"], 0.6)

    def test_build_entries_source_is_instagram_research(self):
        entries = self.scorer.build_entries(_stats())
        for entry in entries:
            self.assertEqual(entry["source"], "instagram_research")

    def test_build_entries_skips_items_missing_value(self):
        stats = _stats(hook_statistics={"sample_size": 5, "top": [{"count": 5}]})
        entries = self.scorer.build_entries(stats)
        self.assertFalse(any(e["type"] == "hook" for e in entries))


if __name__ == "__main__":
    unittest.main()
