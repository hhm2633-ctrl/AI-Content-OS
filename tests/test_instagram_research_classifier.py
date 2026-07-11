import unittest

from modules.instagram_research.instagram_classifier import (
    CLASSIFIER_VERSION,
    CTA_TYPES,
    HOOK_TYPES,
    PATTERN_TYPES,
    classify_cta,
    classify_hook,
    classify_pattern,
    classify_post,
)


class TestInstagramClassifier(unittest.TestCase):
    def test_classify_cta_only_returns_supported_values(self):
        for caption in ("댓글에 남겨주세요", "dm으로 보내주세요", "팔로우 해주세요", "제가 아는 이야기", ""):
            self.assertIn(classify_cta(caption)["value"], CTA_TYPES + ("unknown",))

    def test_classify_evidence_text_is_substring_of_caption_when_matched(self):
        caption = "저장해두시면 나중에 편해요"
        result = classify_cta(caption)
        self.assertIsNotNone(result["evidence_text"])
        self.assertIn(result["evidence_text"], caption)

    def test_classify_funnel_pattern_from_real_observed_caption(self):
        caption = "궁금하신 분들은 댓글 남겨주시면 자료 보내드릴게요"
        result = classify_pattern(caption)
        self.assertEqual(result["value"], "funnel")

    def test_classify_hook_only_returns_supported_values(self):
        for caption in ("진짜 답답했어요", "몰랐다면 실화입니다", "8년차 전문가입니다", ""):
            self.assertIn(classify_hook(caption)["value"], HOOK_TYPES + ("unknown",))

    def test_classify_pattern_only_returns_supported_values(self):
        for caption in ("3가지 방법 알려드려요", "차이 비교해봤어요", "제가 겪은 이야기", ""):
            self.assertIn(classify_pattern(caption)["value"], PATTERN_TYPES + ("unknown",))

    def test_classify_pattern_returns_unknown_for_empty_caption(self):
        result = classify_pattern("")
        self.assertEqual(result["value"], "unknown")
        self.assertEqual(result["reason"], "no_caption_text")

    def test_classify_pattern_returns_unknown_reason_when_no_evidence(self):
        result = classify_pattern("오늘 날씨가 좋네요")
        self.assertEqual(result["value"], "unknown")
        self.assertEqual(result["reason"], "no_supported_keyword_match")

    def test_classify_post_handles_missing_caption_without_raising(self):
        result = classify_post({"account_handle": "brand"})
        self.assertEqual(result["hook"]["value"], "unknown")
        self.assertEqual(result["cta"]["value"], "unknown")
        self.assertEqual(result["pattern"]["value"], "unknown")

    def test_classify_post_handles_non_dict_input_without_raising(self):
        result = classify_post(None)
        self.assertIsNone(result["account_handle"])
        self.assertEqual(result["hook"]["value"], "unknown")

    def test_classify_post_returns_pattern_hook_cta_bundle(self):
        result = classify_post({"account_handle": "brand", "post_shortcode": "abc", "caption_text": "저장 꿀팁"})
        self.assertIn("hook", result)
        self.assertIn("cta", result)
        self.assertIn("pattern", result)
        self.assertEqual(result["account_handle"], "brand")
        self.assertEqual(result["post_shortcode"], "abc")

    def test_classify_result_confidence_within_valid_range(self):
        for fn in (classify_hook, classify_cta, classify_pattern):
            for caption in ("저장해두세요 꿀팁 모음", "", None):
                confidence = fn(caption)["confidence"]
                self.assertGreaterEqual(confidence, 0.0)
                self.assertLessEqual(confidence, 1.0)

    def test_classify_result_has_manually_observed_and_inferred_flags(self):
        result = classify_hook("답답하셨죠")
        self.assertTrue(result["manually_observed"])
        self.assertTrue(result["inferred"])

    def test_classify_result_includes_classifier_version(self):
        self.assertEqual(classify_hook("")["classifier_version"], CLASSIFIER_VERSION)


if __name__ == "__main__":
    unittest.main()
