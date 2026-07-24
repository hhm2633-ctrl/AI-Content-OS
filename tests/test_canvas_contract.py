import unittest

from modules.card_news.canvas_contract import (
    ALLOWED_CARD_CANVAS_SIZES,
    CARD_NEWS_CANVAS_PROFILES,
    DEFAULT_CARD_CANVAS_SIZE,
    DEFAULT_CARD_NEWS_PROFILE_ID,
    INSTAGRAM_CANVAS_PROFILES,
    card_canvas_size,
    get_card_canvas_profile,
)
from modules.tool_adapters.cardnews_renderer_runtime import (
    ALLOWED_CANVAS_SIZES,
    CANVAS_PROFILES,
)


class CanvasContractTests(unittest.TestCase):
    def test_central_contract_declares_feed_and_fullscreen_presets(self):
        self.assertEqual(
            {
                (1080, 566),
                (1080, 1080),
                (1080, 1440),
            },
            set(ALLOWED_CARD_CANVAS_SIZES),
        )
        self.assertEqual(
            (1080, 1920),
            (
                INSTAGRAM_CANVAS_PROFILES["instagram_fullscreen_9_16"]["width"],
                INSTAGRAM_CANVAS_PROFILES["instagram_fullscreen_9_16"]["height"],
            ),
        )

    def test_default_cardnews_canvas_is_explicit_and_resolvable(self):
        self.assertEqual("instagram_portrait_3_4", DEFAULT_CARD_NEWS_PROFILE_ID)
        self.assertEqual((1080, 1440), DEFAULT_CARD_CANVAS_SIZE)
        self.assertEqual(DEFAULT_CARD_CANVAS_SIZE, card_canvas_size())
        self.assertIsNotNone(get_card_canvas_profile())

    def test_renderer_consumes_the_exact_central_feed_contract(self):
        self.assertEqual(CARD_NEWS_CANVAS_PROFILES, CANVAS_PROFILES)
        self.assertEqual(ALLOWED_CARD_CANVAS_SIZES, ALLOWED_CANVAS_SIZES)

    def test_fullscreen_profile_cannot_be_selected_for_cardnews(self):
        self.assertIsNone(get_card_canvas_profile("instagram_fullscreen_9_16"))


if __name__ == "__main__":
    unittest.main()
