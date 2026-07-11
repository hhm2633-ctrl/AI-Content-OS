import unittest

from modules.instagram_research.instagram_statistics import compute_statistics


class TestInstagramResearchStatistics(unittest.TestCase):
    def test_average_caption_length_computed_correctly(self):
        posts = [
            {"caption_text": "abc", "caption_length": 3},
            {"caption_text": "abcdefg", "caption_length": 7},
        ]
        stats = compute_statistics(posts, [])
        self.assertEqual(stats["caption_length_avg"], 5.0)

    def test_average_ignores_none_values(self):
        posts = [
            {"caption_text": "abc", "caption_length": 3},
            {"caption_text": None, "caption_length": 0},
        ]
        stats = compute_statistics(posts, [])
        self.assertEqual(stats["caption_length_observed_count"], 1)
        self.assertEqual(stats["caption_length_avg"], 3.0)

    def test_empty_dataset_does_not_raise_and_returns_zeroes(self):
        stats = compute_statistics([], [])
        self.assertEqual(stats["total_posts"], 0)
        self.assertEqual(stats["total_accounts"], 0)
        self.assertEqual(stats["caption_length_avg"], 0.0)

    def test_missing_post_type_counted_as_unknown(self):
        posts = [{"account_handle": "brand"}]
        stats = compute_statistics(posts, [])
        self.assertEqual(stats["post_type_distribution"].get("unknown"), 1)

    def test_none_dataset_does_not_raise(self):
        stats = compute_statistics(None, None)
        self.assertEqual(stats["total_posts"], 0)

    def test_pattern_hook_cta_distribution_from_classifications(self):
        classifications = [
            {"hook": {"value": "pain_point"}, "cta": {"value": "save"}, "pattern": {"value": "story"}},
            {"hook": {"value": "pain_point"}, "cta": {"value": "unknown"}, "pattern": {"value": "unknown"}},
        ]
        stats = compute_statistics([], classifications)
        self.assertEqual(stats["hook_distribution"]["pain_point"], 2)
        self.assertEqual(stats["cta_distribution"]["save"], 1)
        self.assertEqual(stats["unknown_counts"]["cta"], 1)
        self.assertEqual(stats["unknown_counts"]["pattern"], 1)

    def test_post_type_distribution_counts_correctly(self):
        posts = [
            {"post_type": "carousel"},
            {"post_type": "carousel"},
            {"post_type": "reel"},
        ]
        stats = compute_statistics(posts, [])
        self.assertEqual(stats["post_type_distribution"]["carousel"], 2)
        self.assertEqual(stats["post_type_distribution"]["reel"], 1)

    def test_statistics_includes_generated_at_timestamp(self):
        stats = compute_statistics([], [])
        self.assertIn("generated_at", stats)
        self.assertIsInstance(stats["generated_at"], str)
        self.assertTrue(len(stats["generated_at"]) > 0)

    def test_total_posts_and_accounts_counted_correctly(self):
        posts = [
            {"account_handle": "brand_a"},
            {"account_handle": "brand_a"},
            {"account_handle": "brand_b"},
        ]
        stats = compute_statistics(posts, [])
        self.assertEqual(stats["total_posts"], 3)
        self.assertEqual(stats["total_accounts"], 2)


if __name__ == "__main__":
    unittest.main()
