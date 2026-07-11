import unittest

from modules.competitor_learning.competitor_learning_dashboard import CompetitorLearningDashboard


def _statistics(**overrides):
    base = {
        "sample_size": 3,
        "hook_statistics": {"top": [{"value": "attention", "count": 2}]},
        "cta_statistics": {"top": [{"value": "save", "count": 2}]},
        "pattern_statistics": {"top": [{"value": "funnel", "count": 1}]},
        "layout_statistics": {"top_layouts": [{"value": "carousel", "count": 2}]},
        "competitor_statistics": {
            "account_count": 2,
            "accounts": {
                "brand_a": {"post_count": 2, "avg_likes": 100.0, "avg_comments": 10.0},
                "brand_b": {"post_count": 1, "avg_likes": 200.0, "avg_comments": 20.0},
            },
        },
        "caption_summary": {"avg_caption_length": 30.0},
    }
    base.update(overrides)
    return base


class TestCompetitorLearningDashboard(unittest.TestCase):
    def setUp(self):
        self.dashboard = CompetitorLearningDashboard()

    def test_build_includes_generated_at_timestamp(self):
        report = self.dashboard.build(_statistics(), {})
        self.assertIn("generated_at", report)
        self.assertTrue(len(report["generated_at"]) > 0)

    def test_build_analyzed_account_count_from_competitor_statistics(self):
        report = self.dashboard.build(_statistics(), {})
        self.assertEqual(report["analyzed_account_count"], 2)

    def test_build_analyzed_post_count_from_sample_size(self):
        report = self.dashboard.build(_statistics(), {})
        self.assertEqual(report["analyzed_post_count"], 3)

    def test_build_hook_top10_capped_at_ten(self):
        many_hooks = {"top": [{"value": f"h{i}", "count": i} for i in range(15)]}
        report = self.dashboard.build(_statistics(hook_statistics=many_hooks), {})
        self.assertEqual(len(report["hook_top10"]), 10)

    def test_build_avg_likes_weighted_by_post_count(self):
        report = self.dashboard.build(_statistics(), {})
        # (100*2 + 200*1) / 3 = 133.33
        self.assertEqual(report["avg_likes"], 133.33)

    def test_build_avg_likes_none_when_no_engagement_observed(self):
        stats = _statistics(competitor_statistics={"account_count": 1, "accounts": {"brand_a": {"post_count": 1}}})
        report = self.dashboard.build(stats, {})
        self.assertIsNone(report["avg_likes"])

    def test_build_new_learning_count_from_knowledge_database(self):
        report = self.dashboard.build(_statistics(), {"new_count": 4})
        self.assertEqual(report["new_learning_count"], 4)

    def test_build_fallback_used_true_when_sample_size_zero(self):
        report = self.dashboard.build(_statistics(sample_size=0), {})
        self.assertTrue(report["fallback_used"])

    def test_build_fallback_used_false_when_sample_size_positive(self):
        report = self.dashboard.build(_statistics(), {})
        self.assertFalse(report["fallback_used"])

    def test_build_handles_missing_statistics_gracefully(self):
        report = self.dashboard.build({}, {})
        self.assertEqual(report["analyzed_post_count"], 0)
        self.assertEqual(report["hook_top10"], [])

    def test_build_handles_none_inputs_gracefully(self):
        report = self.dashboard.build(None, None)
        self.assertEqual(report["analyzed_post_count"], 0)

    def test_build_caption_summary_passthrough(self):
        report = self.dashboard.build(_statistics(), {})
        self.assertEqual(report["caption_summary"]["avg_caption_length"], 30.0)


if __name__ == "__main__":
    unittest.main()
