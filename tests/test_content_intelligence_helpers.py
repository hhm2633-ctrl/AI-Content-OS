import unittest
from unittest.mock import patch

from modules.content.brand_rule_evaluator import BrandRuleEvaluator
from modules.content.content_duplicate_detector import ContentDuplicateDetector
from modules.content.content_quality_scorer import ContentQualityScorer
from modules.content.publishing_hint_generator import PublishingHintGenerator


def _complete_content():
    return {
        "title": "AI 자동화 시작 가이드",
        "caption": "AI 자동화를 작은 반복 업무부터 안전하게 시작하는 순서입니다.",
        "hashtags": ["#AI", "#자동화", "#가이드"],
        "prompt_source": "pattern_aware",
        "slides": [
            {"role": "hook", "headline": "AI 자동화 시작", "body": "반복 업무 한 가지부터 줄여보세요."},
            {"role": "problem", "headline": "처음엔 작게", "body": "큰 시스템보다 반복되는 한 단계를 고릅니다."},
            {"role": "solution", "headline": "결과를 검수", "body": "자동화 결과를 사람이 확인하는 단계를 둡니다."},
            {"role": "cta", "headline": "가이드를 저장", "body": "필요할 때 다시 볼 수 있게 저장하세요."},
        ],
    }


class TestBrandRuleEvaluator(unittest.TestCase):
    def setUp(self):
        self.evaluator = BrandRuleEvaluator()
        self.evaluator.brand_profile = {"banned_words": ["대박", "확정 수익"]}

    def test_clean_complete_content_passes(self):
        result = self.evaluator.evaluate(_complete_content())
        self.assertTrue(result["brand_rule_passed"])
        self.assertEqual(result["violations"], [])

    def test_banned_and_exaggerated_claims_fail(self):
        content = _complete_content()
        content["caption"] = "무조건 수익, 확정 수익으로 대박을 보장합니다."
        result = self.evaluator.evaluate(content)
        self.assertFalse(result["brand_rule_passed"])
        self.assertTrue(any(item.startswith("banned_word:") for item in result["violations"]))
        self.assertTrue(any(item.startswith("exaggerated_claim:") for item in result["violations"]))

    def test_missing_title_or_caption_fails_tone_gate(self):
        result = self.evaluator.evaluate({"title": "제목만 있음", "caption": ""})
        self.assertFalse(result["tone_match"])
        self.assertFalse(result["brand_rule_passed"])


class TestContentDuplicateDetector(unittest.TestCase):
    def test_identical_title_hook_and_cta_are_high_risk(self):
        detector = ContentDuplicateDetector()
        content = _complete_content()
        hook, cta = detector._extract_hook_cta_text(content)
        history = {"records": [{"title": content["title"], "hook_text": hook, "cta_text": cta}]}
        with patch.object(detector, "_load_history", return_value=history):
            result = detector.check(content)
        self.assertEqual(result["duplicate_risk"], "high")
        self.assertEqual(result["similarity_score"], 1.0)

    def test_empty_or_corrupt_history_is_safe_low_risk(self):
        detector = ContentDuplicateDetector()
        with patch.object(detector, "_load_history", return_value={"records": "invalid"}):
            result = detector.check(_complete_content())
        self.assertEqual(result["duplicate_risk"], "low")
        self.assertEqual(result["checked_against"], 0)


class TestContentQualityScorer(unittest.TestCase):
    def test_complete_pattern_aware_content_scores_and_records_confidence_bonus(self):
        result = ContentQualityScorer().score(
            _complete_content(),
            research_result={
                "keyword": "AI 자동화",
                "topic_intelligence": {"keywords": ["자동화"], "confidence_score": 1.0},
            },
            prompt_meta={"hook_score": 1.0, "cta_score": 1.0, "pattern_fallback_used": False},
            brand_result={"brand_rule_passed": True},
        )
        self.assertEqual(result["quality_score"], 1.0)
        self.assertEqual(result["checks"]["pattern_confidence_bonus"], 5)

    def test_fallback_and_duplicate_slides_reduce_score_without_raising(self):
        content = _complete_content()
        content["fallback_used"] = True
        content["slides"][1] = dict(content["slides"][0])
        result = ContentQualityScorer().score(content, research_result={"keyword": "AI 자동화"})
        self.assertTrue(result["checks"]["fallback_used"])
        self.assertGreater(result["checks"]["duplicate_slide_penalty"], 0)
        self.assertLess(result["quality_score"], 1.0)


class TestPublishingHintGenerator(unittest.TestCase):
    def test_explicit_cta_and_pattern_control_recommendations(self):
        result = PublishingHintGenerator().generate(
            _complete_content(), {"pattern_type": "tutorial"}, cta_type="comment"
        )
        self.assertEqual(result["recommended_action"], "comment")
        self.assertIn("댓글", result["caption_direction"])
        self.assertIn("#방법", result["hashtag_direction"])

    def test_cta_is_inferred_and_unknown_value_falls_back_to_save(self):
        generator = PublishingHintGenerator()
        inferred = generator.generate(_complete_content(), {})
        unknown = generator.generate(_complete_content(), {}, cta_type="unsupported")
        self.assertEqual(inferred["recommended_action"], "save")
        self.assertEqual(unknown["recommended_action"], "save")
        self.assertEqual(len(inferred["checklist"]), 5)


if __name__ == "__main__":
    unittest.main()
