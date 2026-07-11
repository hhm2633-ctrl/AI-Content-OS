import unittest

from modules.competitor_learning.competitor_learning_extractor import CompetitorLearningExtractor
from modules.instagram_research.instagram_normalizer import build_post_record


class _FakeInterface:
    def __init__(self, posts=None, raise_error=False):
        self._posts = posts if posts is not None else []
        self._raise_error = raise_error

    def get_posts(self, limit=None, account_handle=None):
        if self._raise_error:
            raise RuntimeError("boom")
        return self._posts


def _post(**overrides):
    raw = {
        "account_handle": "brand_a",
        "post_url": "https://www.instagram.com/p/ABC123/",
        "post_type": "carousel",
        "caption_text": "저장해두고 필요할 때 보세요 꿀팁 정리",
        "visible_like_text": "1,234",
        "visible_comment_text": "56",
        "slide_count": 4,
        "image_count": 4,
    }
    raw.update(overrides)
    return build_post_record(raw)


class TestCompetitorLearningExtractor(unittest.TestCase):
    def test_extract_returns_empty_list_when_no_posts(self):
        extractor = CompetitorLearningExtractor(interface=_FakeInterface(posts=[]))
        self.assertEqual(extractor.extract(), [])

    def test_extract_returns_empty_list_when_interface_raises(self):
        extractor = CompetitorLearningExtractor(interface=_FakeInterface(raise_error=True))
        self.assertEqual(extractor.extract(), [])

    def test_extract_returns_empty_list_when_interface_returns_none(self):
        extractor = CompetitorLearningExtractor(interface=_FakeInterface(posts=None))
        self.assertEqual(extractor.extract(), [])

    def test_extract_skips_non_dict_posts(self):
        extractor = CompetitorLearningExtractor(interface=_FakeInterface(posts=["not_a_dict", None, 123]))
        self.assertEqual(extractor.extract(), [])

    def test_extract_builds_observation_with_hook_cta_pattern_from_classification(self):
        extractor = CompetitorLearningExtractor(interface=_FakeInterface(posts=[_post()]))
        observations = extractor.extract()
        self.assertEqual(len(observations), 1)
        observation = observations[0]
        self.assertIn("hook_type", observation)
        self.assertIn("cta_type", observation)
        self.assertIn("pattern_type", observation)
        self.assertEqual(observation["hook_type"], "saveable_tip")
        self.assertEqual(observation["cta_type"], "save")

    def test_extract_parses_like_and_comment_counts(self):
        extractor = CompetitorLearningExtractor(interface=_FakeInterface(posts=[_post()]))
        observation = extractor.extract()[0]
        self.assertEqual(observation["like_count"], 1234)
        self.assertEqual(observation["comment_count"], 56)

    def test_extract_defaults_hook_type_to_unknown_when_no_caption(self):
        extractor = CompetitorLearningExtractor(interface=_FakeInterface(posts=[_post(caption_text=None)]))
        observation = extractor.extract()[0]
        self.assertEqual(observation["hook_type"], "unknown")
        self.assertEqual(observation["cta_type"], "unknown")
        self.assertEqual(observation["pattern_type"], "unknown")

    def test_extract_defaults_post_type_to_unknown_when_missing(self):
        extractor = CompetitorLearningExtractor(interface=_FakeInterface(posts=[_post(post_type=None)]))
        observation = extractor.extract()[0]
        self.assertEqual(observation["post_type"], "unknown")

    def test_extract_preserves_account_handle_and_shortcode(self):
        extractor = CompetitorLearningExtractor(interface=_FakeInterface(posts=[_post(account_handle="brand_x")]))
        observation = extractor.extract()[0]
        self.assertEqual(observation["account_handle"], "brand_x")
        self.assertEqual(observation["post_shortcode"], "ABC123")

    def test_extract_hashtags_default_to_empty_list(self):
        extractor = CompetitorLearningExtractor(interface=_FakeInterface(posts=[_post(caption_text="글")]))
        observation = extractor.extract()[0]
        self.assertEqual(observation["hashtags"], [])

    def test_extract_never_raises_on_classification_failure(self):
        extractor = CompetitorLearningExtractor(interface=_FakeInterface(posts=[{"account_handle": "brand_a"}]))
        observations = extractor.extract()
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0]["hook_type"], "unknown")

    def test_extract_multiple_posts_all_included(self):
        posts = [_post(post_url=f"https://www.instagram.com/p/{i}/") for i in range(5)]
        extractor = CompetitorLearningExtractor(interface=_FakeInterface(posts=posts))
        self.assertEqual(len(extractor.extract()), 5)

    def test_extract_confidence_fields_are_numeric(self):
        extractor = CompetitorLearningExtractor(interface=_FakeInterface(posts=[_post()]))
        observation = extractor.extract()[0]
        self.assertIsInstance(observation["hook_confidence"], (int, float))
        self.assertIsInstance(observation["cta_confidence"], (int, float))
        self.assertIsInstance(observation["pattern_confidence"], (int, float))

    def test_extract_like_count_none_when_visible_text_missing(self):
        extractor = CompetitorLearningExtractor(
            interface=_FakeInterface(posts=[_post(visible_like_text=None, visible_comment_text=None)])
        )
        observation = extractor.extract()[0]
        self.assertIsNone(observation["like_count"])
        self.assertIsNone(observation["comment_count"])

    def test_extract_uses_default_interface_when_none_provided(self):
        extractor = CompetitorLearningExtractor()
        self.assertIsNotNone(extractor.interface)


if __name__ == "__main__":
    unittest.main()
