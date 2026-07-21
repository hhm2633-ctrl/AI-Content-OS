"""Independent coverage for modules/performance_score/performance_score_calculator.py.

Priority-2 gap-fill test: this calculator has no dedicated test file today
despite being pure (no I/O, no network) and high-leverage (Audit Engine and
Analytics Engine both read its output via PerformanceScoreInterface). No
existing module or test file is modified.
"""

import unittest

from modules.performance_score.performance_score_calculator import PerformanceScoreCalculator


class PerformanceScoreCalculatorTests(unittest.TestCase):
    def setUp(self):
        self.calculator = PerformanceScoreCalculator()

    def test_all_missing_inputs_yield_default_scores(self):
        result = self.calculator.calculate()

        self.assertEqual(result["hook_score"], 0.5)
        self.assertEqual(result["cta_score"], 0.5)
        self.assertEqual(result["layout_score"], 0.5)
        self.assertEqual(result["brand_score"], 0.5)
        self.assertEqual(result["image_score"], 0.5)
        self.assertEqual(result["overall_performance_score"], 0.5)

    def test_hook_score_prefers_explicit_pattern_prompt_meta_value(self):
        content_result = {"pattern_prompt_meta": {"hook_score": 0.8}}
        result = self.calculator.calculate(content_result=content_result)
        self.assertEqual(result["hook_score"], 0.8)

    def test_hook_score_falls_back_to_quality_check_flag(self):
        content_result = {
            "content_intelligence": {"details": {"quality": {"checks": {"hook_present": True}}}},
        }
        result = self.calculator.calculate(content_result=content_result)
        self.assertEqual(result["hook_score"], 1.0)

    def test_cta_score_prefers_explicit_value_over_quality_flag(self):
        content_result = {
            "pattern_prompt_meta": {"cta_score": 0.3},
            "content_intelligence": {"details": {"quality": {"checks": {"cta_present": True}}}},
        }
        result = self.calculator.calculate(content_result=content_result)
        self.assertEqual(result["cta_score"], 0.3)

    def test_layout_score_prefers_layout_quality_score_over_qa_score(self):
        card_news_result = {
            "layout_result": {"layout_quality_score": 0.77},
            "card_news_quality": {"qa_score": 0.1},
        }
        result = self.calculator.calculate(card_news_result=card_news_result)
        self.assertEqual(result["layout_score"], 0.77)

    def test_layout_score_falls_back_to_qa_score_when_layout_quality_missing(self):
        card_news_result = {"card_news_quality": {"qa_score": 0.65}}
        result = self.calculator.calculate(card_news_result=card_news_result)
        self.assertEqual(result["layout_score"], 0.65)

    def test_brand_score_passed_is_full_score(self):
        content_result = {"content_intelligence": {"brand_rule_passed": True}}
        result = self.calculator.calculate(content_result=content_result)
        self.assertEqual(result["brand_score"], 1.0)

    def test_brand_score_failed_is_low_score(self):
        content_result = {"content_intelligence": {"brand_rule_passed": False}}
        result = self.calculator.calculate(content_result=content_result)
        self.assertEqual(result["brand_score"], 0.2)

    def test_image_score_fallback_used_is_low(self):
        result = self.calculator.calculate(image_strategy_result={"fallback_used": True})
        self.assertEqual(result["image_score"], 0.3)

    def test_image_score_real_image_not_needed_is_high(self):
        result = self.calculator.calculate(image_strategy_result={"need_ai_image": False})
        self.assertEqual(result["image_score"], 0.9)

    def test_image_score_ai_image_path_is_medium(self):
        result = self.calculator.calculate(image_strategy_result={"need_ai_image": True})
        self.assertEqual(result["image_score"], 0.6)

    def test_image_score_empty_dict_is_default(self):
        result = self.calculator.calculate(image_strategy_result={})
        self.assertEqual(result["image_score"], 0.5)

    def test_overall_score_is_weighted_sum_of_components(self):
        content_result = {"pattern_prompt_meta": {"hook_score": 1.0, "cta_score": 1.0}}
        card_news_result = {"layout_result": {"layout_quality_score": 1.0}}
        image_strategy_result = {"need_ai_image": False}  # 0.9

        result = self.calculator.calculate(
            content_result=content_result,
            card_news_result=card_news_result,
            image_strategy_result=image_strategy_result,
        )

        # hook 1.0*0.25 + cta 1.0*0.2 + layout 1.0*0.2 + brand 0.5*0.2 + image 0.9*0.15
        expected = round(1.0 * 0.25 + 1.0 * 0.2 + 1.0 * 0.2 + 0.5 * 0.2 + 0.9 * 0.15, 4)
        self.assertEqual(result["overall_performance_score"], expected)

    def test_score_is_clamped_to_zero_one_range_for_out_of_range_input(self):
        content_result = {"pattern_prompt_meta": {"hook_score": 5.0, "cta_score": -3.0}}
        result = self.calculator.calculate(content_result=content_result)
        self.assertEqual(result["hook_score"], 1.0)
        self.assertEqual(result["cta_score"], 0.0)

    def test_non_numeric_explicit_score_falls_back_to_check_flag_or_default(self):
        content_result = {"pattern_prompt_meta": {"hook_score": "not-a-number"}}
        result = self.calculator.calculate(content_result=content_result)
        self.assertEqual(result["hook_score"], 0.5)

    def test_malformed_content_result_never_raises(self):
        # A completely wrong-shaped input (a list instead of a dict-of-dicts)
        # for a nested field must degrade to the default, never crash.
        content_result = {"pattern_prompt_meta": ["not", "a", "dict"]}
        result = self.calculator.calculate(content_result=content_result)
        self.assertEqual(result["hook_score"], 0.5)

    def test_calculate_is_deterministic_for_same_input(self):
        content_result = {"pattern_prompt_meta": {"hook_score": 0.7, "cta_score": 0.6}}
        result_one = self.calculator.calculate(content_result=content_result)
        result_two = self.calculator.calculate(content_result=dict(content_result))
        self.assertEqual(result_one, result_two)


if __name__ == "__main__":
    unittest.main()
