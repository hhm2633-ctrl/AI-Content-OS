import unittest

from modules.instagram_research.instagram_normalizer import (
    count_emoji,
    count_hashtags,
    dedupe_posts,
    extract_shortcode,
    normalize_caption,
    normalize_url,
    parse_visible_count_text,
    sanitize_screenshot_path,
)


class TestInstagramNormalizer(unittest.TestCase):
    def test_count_emoji_counts_emoji_characters(self):
        self.assertEqual(count_emoji("great post \U0001F525\U0001F525"), 2)

    def test_count_emoji_returns_none_for_none_input(self):
        self.assertIsNone(count_emoji(None))

    def test_count_emoji_returns_zero_for_plain_text(self):
        self.assertEqual(count_emoji("plain text, no emoji"), 0)

    def test_count_hashtags_counts_list_length(self):
        self.assertEqual(count_hashtags(["#a", "#b", "#c"]), 3)

    def test_count_hashtags_returns_none_for_none_input(self):
        self.assertIsNone(count_hashtags(None))

    def test_count_hashtags_returns_zero_for_empty_list(self):
        self.assertEqual(count_hashtags([]), 0)

    def test_count_hashtags_zero_and_none_are_distinguishable(self):
        self.assertNotEqual(count_hashtags([]), count_hashtags(None))

    def test_dedupe_posts_handles_empty_list(self):
        deduped, duplicate_count = dedupe_posts([])
        self.assertEqual(deduped, [])
        self.assertEqual(duplicate_count, 0)

    def test_dedupe_posts_handles_none_input(self):
        deduped, duplicate_count = dedupe_posts(None)
        self.assertEqual(deduped, [])
        self.assertEqual(duplicate_count, 0)

    def test_dedupe_posts_removes_duplicate_shortcodes(self):
        posts = [
            {"account_handle": "brand", "post_shortcode": "abc"},
            {"account_handle": "brand", "post_shortcode": "abc"},
            {"account_handle": "brand", "post_shortcode": "def"},
        ]
        deduped, duplicate_count = dedupe_posts(posts)
        self.assertEqual(len(deduped), 2)
        self.assertEqual(duplicate_count, 1)

    def test_extract_shortcode_from_post_url(self):
        self.assertEqual(
            extract_shortcode("https://www.instagram.com/p/ABC123/"), "ABC123"
        )

    def test_extract_shortcode_from_reel_url(self):
        self.assertEqual(
            extract_shortcode("https://www.instagram.com/reel/XYZ789/"), "XYZ789"
        )

    def test_extract_shortcode_returns_none_for_non_post_url(self):
        self.assertIsNone(extract_shortcode("https://www.instagram.com/somebrand/"))

    def test_extract_shortcode_returns_none_for_none_input(self):
        self.assertIsNone(extract_shortcode(None))

    def test_normalize_caption_computes_length_and_first_line(self):
        metrics = normalize_caption("hello world\nsecond line")
        self.assertEqual(metrics["caption_length"], len("hello world\nsecond line"))
        self.assertEqual(metrics["first_line"], "hello world")

    def test_normalize_caption_counts_line_breaks(self):
        metrics = normalize_caption("line1\nline2\nline3")
        self.assertEqual(metrics["line_break_count"], 2)

    def test_normalize_caption_handles_none_without_raising(self):
        metrics = normalize_caption(None)
        self.assertEqual(metrics["caption_length"], 0)
        self.assertEqual(metrics["hashtags"], [])

    def test_normalize_url_adds_domain_for_relative_path(self):
        self.assertEqual(
            normalize_url("/reel/ABC123/"), "https://www.instagram.com/reel/ABC123"
        )

    def test_normalize_url_returns_none_for_empty_input(self):
        self.assertIsNone(normalize_url(""))
        self.assertIsNone(normalize_url(None))

    def test_normalize_url_strips_tracking_query_params(self):
        self.assertEqual(
            normalize_url("https://www.instagram.com/p/ABC123/?utm_source=ig_web_copy_link"),
            "https://www.instagram.com/p/ABC123",
        )

    def test_normalize_url_strips_trailing_slash(self):
        self.assertEqual(
            normalize_url("https://www.instagram.com/p/ABC123/"),
            "https://www.instagram.com/p/ABC123",
        )

    def test_parse_visible_count_text_comma_formatted(self):
        self.assertEqual(parse_visible_count_text("1,234"), 1234)

    def test_parse_visible_count_text_exact_number(self):
        self.assertEqual(parse_visible_count_text("5000"), 5000)

    def test_parse_visible_count_text_korean_ten_thousand_unit(self):
        self.assertEqual(parse_visible_count_text("1.2만"), 12000)

    def test_parse_visible_count_text_korean_thousand_unit(self):
        self.assertEqual(parse_visible_count_text("5천"), 5000)

    def test_parse_visible_count_text_none_stays_none(self):
        self.assertIsNone(parse_visible_count_text(None))

    def test_parse_visible_count_text_unparseable_text_returns_none_value(self):
        self.assertIsNone(parse_visible_count_text("많음"))

    def test_sanitize_screenshot_path_accepts_valid_path(self):
        path = "storage/research/instagram/screenshots/abc.png"
        self.assertEqual(sanitize_screenshot_path(path), path)

    def test_sanitize_screenshot_path_rejects_absolute_path(self):
        self.assertIsNone(sanitize_screenshot_path("/etc/passwd"))
        self.assertIsNone(sanitize_screenshot_path("C:/secrets/file.png"))

    def test_sanitize_screenshot_path_rejects_none(self):
        self.assertIsNone(sanitize_screenshot_path(None))

    def test_sanitize_screenshot_path_rejects_outside_expected_dir(self):
        self.assertIsNone(sanitize_screenshot_path("storage/research/other/abc.png"))

    def test_sanitize_screenshot_path_rejects_parent_traversal(self):
        self.assertIsNone(
            sanitize_screenshot_path("storage/research/instagram/screenshots/../../secrets.txt")
        )


if __name__ == "__main__":
    unittest.main()
