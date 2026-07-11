import unittest

from modules.competitor_learning.competitor_learning_statistics import CompetitorLearningStatistics


def _obs(**overrides):
    base = {
        "account_handle": "brand_a",
        "post_shortcode": "abc",
        "post_type": "carousel",
        "slide_count": 4,
        "image_count": 4,
        "caption_length": 20,
        "hashtag_count": 2,
        "hashtags": ["#ai", "#tip"],
        "like_count": 100,
        "comment_count": 10,
        "hook_type": "saveable_tip",
        "hook_confidence": 0.55,
        "cta_type": "save",
        "cta_confidence": 0.55,
        "pattern_type": "number_list",
        "pattern_confidence": 0.55,
    }
    base.update(overrides)
    return base


class TestCompetitorLearningStatistics(unittest.TestCase):
    def setUp(self):
        self.stats = CompetitorLearningStatistics()

    def test_compute_empty_observations_returns_zeroed_structures(self):
        result = self.stats.compute([])
        self.assertEqual(result["sample_size"], 0)
        self.assertEqual(result["hook_statistics"]["distribution"], {})
        self.assertEqual(result["competitor_statistics"]["account_count"], 0)

    def test_compute_none_observations_does_not_raise(self):
        result = self.stats.compute(None)
        self.assertEqual(result["sample_size"], 0)

    def test_compute_ignores_non_dict_observations(self):
        result = self.stats.compute([_obs(), "garbage", None, 123])
        self.assertEqual(result["sample_size"], 1)

    def test_compute_sample_size_matches_observation_count(self):
        observations = [_obs(), _obs(), _obs()]
        result = self.stats.compute(observations)
        self.assertEqual(result["sample_size"], 3)

    def test_hook_statistics_distribution_counts_correctly(self):
        observations = [_obs(hook_type="attention"), _obs(hook_type="attention"), _obs(hook_type="pain_point")]
        result = self.stats.compute(observations)
        self.assertEqual(result["hook_statistics"]["distribution"]["attention"], 2)
        self.assertEqual(result["hook_statistics"]["distribution"]["pain_point"], 1)

    def test_hook_statistics_top_sorted_by_count_desc(self):
        observations = [_obs(hook_type="attention")] * 3 + [_obs(hook_type="pain_point")]
        result = self.stats.compute(observations)
        top = result["hook_statistics"]["top"]
        self.assertEqual(top[0]["value"], "attention")
        self.assertEqual(top[0]["count"], 3)

    def test_hook_statistics_unknown_count_tracked(self):
        observations = [_obs(hook_type="unknown"), _obs(hook_type="unknown"), _obs(hook_type="attention")]
        result = self.stats.compute(observations)
        self.assertEqual(result["hook_statistics"]["unknown_count"], 2)

    def test_hook_statistics_avg_likes_computed_per_value(self):
        observations = [_obs(hook_type="attention", like_count=100), _obs(hook_type="attention", like_count=200)]
        result = self.stats.compute(observations)
        top = result["hook_statistics"]["top"]
        self.assertEqual(top[0]["avg_likes"], 150.0)

    def test_cta_statistics_avg_confidence_computed(self):
        observations = [_obs(cta_type="save", cta_confidence=0.5), _obs(cta_type="save", cta_confidence=0.7)]
        result = self.stats.compute(observations)
        top = result["cta_statistics"]["top"]
        self.assertEqual(top[0]["avg_confidence"], 0.6)

    def test_pattern_statistics_distribution_counts_correctly(self):
        observations = [_obs(pattern_type="funnel"), _obs(pattern_type="story")]
        result = self.stats.compute(observations)
        self.assertEqual(result["pattern_statistics"]["distribution"], {"funnel": 1, "story": 1})

    def test_layout_statistics_uses_post_type_not_layout_selector_vocab(self):
        observations = [_obs(post_type="reel"), _obs(post_type="carousel")]
        result = self.stats.compute(observations)
        values = {item["value"] for item in result["layout_statistics"]["top_layouts"]}
        self.assertEqual(values, {"reel", "carousel"})
        self.assertNotIn("bold_ai", values)
        self.assertNotIn("notebook", values)

    def test_layout_statistics_avg_slide_and_image_count(self):
        observations = [_obs(slide_count=2, image_count=2), _obs(slide_count=4, image_count=4)]
        result = self.stats.compute(observations)
        self.assertEqual(result["layout_statistics"]["avg_slide_count"], 3.0)
        self.assertEqual(result["layout_statistics"]["avg_image_count"], 3.0)

    def test_layout_statistics_includes_vocabulary_note(self):
        result = self.stats.compute([_obs()])
        self.assertIn("vocabulary_note", result["layout_statistics"])
        self.assertTrue(len(result["layout_statistics"]["vocabulary_note"]) > 0)

    def test_competitor_statistics_groups_by_account_handle(self):
        observations = [_obs(account_handle="brand_a"), _obs(account_handle="brand_b"), _obs(account_handle="brand_a")]
        result = self.stats.compute(observations)
        accounts = result["competitor_statistics"]["accounts"]
        self.assertEqual(accounts["brand_a"]["post_count"], 2)
        self.assertEqual(accounts["brand_b"]["post_count"], 1)

    def test_competitor_statistics_dominant_values_per_account(self):
        observations = [
            _obs(account_handle="brand_a", hook_type="attention"),
            _obs(account_handle="brand_a", hook_type="attention"),
            _obs(account_handle="brand_a", hook_type="pain_point"),
        ]
        result = self.stats.compute(observations)
        self.assertEqual(result["competitor_statistics"]["accounts"]["brand_a"]["dominant_hook_type"], "attention")

    def test_competitor_statistics_top_hashtags_per_account(self):
        observations = [
            _obs(account_handle="brand_a", hashtags=["#a", "#b"]),
            _obs(account_handle="brand_a", hashtags=["#a"]),
        ]
        result = self.stats.compute(observations)
        top_hashtags = result["competitor_statistics"]["accounts"]["brand_a"]["top_hashtags"]
        self.assertEqual(top_hashtags[0], "#a")

    def test_competitor_statistics_account_count_correct(self):
        observations = [_obs(account_handle="brand_a"), _obs(account_handle="brand_b")]
        result = self.stats.compute(observations)
        self.assertEqual(result["competitor_statistics"]["account_count"], 2)

    def test_caption_summary_avg_caption_length(self):
        observations = [_obs(caption_length=10), _obs(caption_length=20)]
        result = self.stats.compute(observations)
        self.assertEqual(result["caption_summary"]["avg_caption_length"], 15.0)

    def test_caption_summary_top_hashtags_overall(self):
        observations = [_obs(hashtags=["#a"]), _obs(hashtags=["#a"]), _obs(hashtags=["#b"])]
        result = self.stats.compute(observations)
        top_hashtags = result["caption_summary"]["top_hashtags"]
        self.assertEqual(top_hashtags[0]["hashtag"], "#a")
        self.assertEqual(top_hashtags[0]["count"], 2)

    def test_caption_summary_handles_no_hashtags(self):
        observations = [_obs(hashtags=[])]
        result = self.stats.compute(observations)
        self.assertEqual(result["caption_summary"]["top_hashtags"], [])

    def test_avg_helper_ignores_bool_values(self):
        # caption_length=True는 int의 서브클래스지만 실제로 숫자 관측이 아니므로
        # 평균 계산에서 제외되어야 한다.
        observations = [_obs(caption_length=True), _obs(caption_length=10)]
        result = self.stats.compute(observations)
        self.assertEqual(result["caption_summary"]["avg_caption_length"], 10.0)

    def test_avg_helper_returns_none_when_no_numeric_values(self):
        observations = [_obs(caption_length=None)]
        result = self.stats.compute(observations)
        self.assertIsNone(result["caption_summary"]["avg_caption_length"])


if __name__ == "__main__":
    unittest.main()
