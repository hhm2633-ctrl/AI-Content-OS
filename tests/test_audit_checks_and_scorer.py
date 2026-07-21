"""Independent coverage for modules/audit_engine/audit_checks.py and audit_score.py.

Priority-2 gap-fill (continuation of the long autonomous maintainability task):
`modules/audit_engine/` had zero tests anywhere in the repo prior to this file.
Both `AuditChecks` and `AuditScorer` are pure (no I/O, no network), reading
only already-computed pipeline signals passed in as plain dicts -- no mocking
needed beyond building synthetic context dicts. No existing module or test
file is modified.
"""

import unittest

from modules.audit_engine.audit_checks import AuditChecks
from modules.audit_engine.audit_score import AuditScorer


def _base_context(**overrides):
    context = {
        "content_result": {},
        "performance_score_result": {},
        "pattern_result": {},
        "card_news_result": {},
        "knowledge_result": {"top_knowledge": []},
        "trend_memory_result": {},
    }
    context.update(overrides)
    return context


class AuditChecksHookCtaTests(unittest.TestCase):
    def setUp(self):
        self.checks = AuditChecks()

    def test_hook_check_passes_when_present_and_score_above_threshold(self):
        context = _base_context(performance_score_result={"hook_score": 0.8})
        result = self.checks._hook_check(context)
        self.assertTrue(result["passed"])
        self.assertEqual(result["score"], 0.8)

    def test_hook_check_fails_when_score_below_threshold(self):
        context = _base_context(performance_score_result={"hook_score": 0.3})
        result = self.checks._hook_check(context)
        self.assertFalse(result["passed"])

    def test_hook_check_fails_when_hook_not_present_even_with_high_score(self):
        context = _base_context(
            content_result={"content_intelligence": {"details": {"quality": {"checks": {"hook_present": False}}}}},
            performance_score_result={"hook_score": 0.9},
        )
        result = self.checks._hook_check(context)
        self.assertFalse(result["passed"])

    def test_cta_check_passes_when_present_and_score_above_threshold(self):
        context = _base_context(performance_score_result={"cta_score": 0.7})
        result = self.checks._cta_check(context)
        self.assertTrue(result["passed"])


class AuditChecksPatternLayoutTests(unittest.TestCase):
    def setUp(self):
        self.checks = AuditChecks()

    def test_pattern_check_neutral_when_not_pattern_aware(self):
        context = _base_context(content_result={"prompt_source": "legacy"})
        result = self.checks._pattern_check(context)
        self.assertTrue(result["passed"])
        self.assertEqual(result["score"], 0.5)

    def test_pattern_check_passes_when_types_match(self):
        context = _base_context(
            content_result={"prompt_source": "pattern_aware", "pattern_prompt_meta": {"pattern_type": "listicle"}},
            pattern_result={"pattern_plan": {"pattern_type": "listicle"}},
        )
        result = self.checks._pattern_check(context)
        self.assertTrue(result["passed"])
        self.assertEqual(result["score"], 1.0)

    def test_pattern_check_fails_when_types_mismatch(self):
        context = _base_context(
            content_result={"prompt_source": "pattern_aware", "pattern_prompt_meta": {"pattern_type": "listicle"}},
            pattern_result={"pattern_plan": {"pattern_type": "story"}},
        )
        result = self.checks._pattern_check(context)
        self.assertFalse(result["passed"])
        self.assertEqual(result["score"], 0.3)

    def test_layout_check_fails_when_fallback_used(self):
        context = _base_context(
            card_news_result={"layout_result": {"fallback_used": True, "layout_type": "notebook"}},
            performance_score_result={"layout_score": 0.9},
        )
        result = self.checks._layout_check(context)
        self.assertFalse(result["passed"])

    def test_layout_check_passes_when_no_fallback_and_score_ok(self):
        context = _base_context(
            card_news_result={"layout_result": {"fallback_used": False, "layout_type": "notebook"}},
            pattern_result={"pattern_plan": {"layout_type": "notebook"}},
            performance_score_result={"layout_score": 0.8},
        )
        result = self.checks._layout_check(context)
        self.assertTrue(result["passed"])
        self.assertTrue(result["layout_matches_plan"])


class AuditChecksBrandImageDuplicateTests(unittest.TestCase):
    def setUp(self):
        self.checks = AuditChecks()

    def test_brand_check_defaults_to_passed_when_flag_absent(self):
        context = _base_context()
        result = self.checks._brand_check(context)
        self.assertTrue(result["passed"])

    def test_brand_check_fails_when_rule_violated(self):
        context = _base_context(content_result={"content_intelligence": {"brand_rule_passed": False}})
        result = self.checks._brand_check(context)
        self.assertFalse(result["passed"])

    def test_image_strategy_check_fails_when_manual_image_required(self):
        context = _base_context(
            card_news_result={"image_sourcing_status": {"manual_image_required": True, "recommended_source": "news"}},
            performance_score_result={"image_score": 0.9},
        )
        result = self.checks._image_strategy_check(context)
        self.assertFalse(result["passed"])
        self.assertTrue(result["manual_image_required"])

    def test_duplicate_check_high_risk_from_content_intelligence(self):
        context = _base_context(content_result={"content_intelligence": {"duplicate_risk": "high"}})
        result = self.checks._duplicate_check(context)
        self.assertFalse(result["passed"])
        self.assertEqual(result["score"], 0.0)

    def test_duplicate_check_high_risk_from_trend_memory(self):
        context = _base_context(trend_memory_result={"topic_repeat_risk": "high"})
        result = self.checks._duplicate_check(context)
        self.assertFalse(result["passed"])

    def test_duplicate_check_high_risk_from_knowledge_top_items(self):
        context = _base_context(knowledge_result={"top_knowledge": [{"duplicate_risk": "high"}]})
        result = self.checks._duplicate_check(context)
        self.assertFalse(result["passed"])
        self.assertEqual(result["knowledge_high_risk_count"], 1)

    def test_duplicate_check_passes_when_all_low(self):
        context = _base_context()
        result = self.checks._duplicate_check(context)
        self.assertTrue(result["passed"])
        self.assertEqual(result["score"], 1.0)

    def test_duplicate_check_malformed_top_knowledge_does_not_crash(self):
        context = _base_context(knowledge_result={"top_knowledge": "not-a-list"})
        result = self.checks._duplicate_check(context)
        self.assertTrue(result["passed"])


class AuditChecksInducementTests(unittest.TestCase):
    def setUp(self):
        self.checks = AuditChecks()

    def test_save_inducement_detected_from_cta_type(self):
        context = _base_context(pattern_result={"pattern_plan": {"cta_type": "save"}})
        result = self.checks._save_inducement_check(context)
        self.assertTrue(result["passed"])

    def test_save_inducement_detected_from_cta_text_keyword(self):
        context = _base_context(content_result={"slides": [{"role": "cta", "headline": "지금 저장하세요", "body": ""}]})
        result = self.checks._save_inducement_check(context)
        self.assertTrue(result["passed"])

    def test_save_inducement_not_detected_without_signal(self):
        context = _base_context(content_result={"slides": [{"role": "cta", "headline": "감사합니다", "body": ""}]})
        result = self.checks._save_inducement_check(context)
        self.assertFalse(result["passed"])

    def test_comment_inducement_detected_from_keyword(self):
        context = _base_context(content_result={"slides": [{"role": "cta", "headline": "댓글로 알려주세요", "body": ""}]})
        result = self.checks._comment_inducement_check(context)
        self.assertTrue(result["passed"])

    def test_extract_cta_text_returns_empty_when_no_cta_slide(self):
        context = _base_context(content_result={"slides": [{"role": "hook", "headline": "x"}]})
        text = self.checks._extract_cta_text(context["content_result"])
        self.assertEqual(text, "")

    def test_extract_cta_text_handles_non_list_slides(self):
        text = self.checks._extract_cta_text({"slides": "not-a-list"})
        self.assertEqual(text, "")


class AuditChecksRunAllTests(unittest.TestCase):
    def test_run_all_returns_all_nine_checks(self):
        checks = AuditChecks()
        result = checks.run_all(_base_context())

        expected_keys = {
            "hook_check", "cta_check", "pattern_check", "layout_check", "brand_check",
            "image_strategy_check", "duplicate_check", "save_inducement_check", "comment_inducement_check",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_run_all_isolates_a_single_check_failure(self):
        checks = AuditChecks()
        context = _base_context()
        del context["content_result"]  # every check reading content_result will KeyError

        result = checks.run_all(context)

        # Every check that reads content_result (hook/cta/pattern/brand/duplicate/
        # save_inducement/comment_inducement) degrades to the safe 0.0/failed
        # shape -- but checks that never touch content_result at all
        # (layout_check, image_strategy_check) are unaffected and still run
        # normally. run_all() must never crash outright either way.
        content_result_dependent = {
            "hook_check", "cta_check", "pattern_check", "brand_check",
            "duplicate_check", "save_inducement_check", "comment_inducement_check",
        }
        for name in content_result_dependent:
            self.assertFalse(result[name]["passed"])
            self.assertEqual(result[name]["score"], 0.0)
            self.assertIn("계산 실패", result[name]["reason"])

        # layout_check/image_strategy_check don't reference content_result, so
        # they still compute their normal (unmet-threshold) result, not a crash.
        self.assertIn("layout_check", result)
        self.assertIn("image_strategy_check", result)


class AuditScorerTests(unittest.TestCase):
    def setUp(self):
        self.scorer = AuditScorer()

    def _all_passing_checks(self):
        return {name: {"passed": True, "score": 1.0} for name in AuditScorer.WEIGHTS}

    def _all_failing_checks(self):
        return {name: {"passed": False, "score": 0.0} for name in AuditScorer.WEIGHTS}

    def test_all_passing_checks_yield_max_score_and_passed_true(self):
        result = self.scorer.score(self._all_passing_checks())
        self.assertEqual(result["audit_score"], 1.0)
        self.assertTrue(result["passed"])
        self.assertEqual(result["recommendations"], ["특별한 개선 필요 사항이 없습니다."])

    def test_all_failing_checks_yield_zero_score_and_failed(self):
        result = self.scorer.score(self._all_failing_checks())
        self.assertEqual(result["audit_score"], 0.0)
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["recommendations"]), len(AuditScorer.WEIGHTS))

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(AuditScorer.WEIGHTS.values()), 1.0, places=6)

    def test_pass_threshold_is_zero_point_six(self):
        checks = self._all_passing_checks()
        # Force exactly 0.6 by zeroing everything except weights that sum near it.
        for name in checks:
            checks[name]["score"] = 0.6
        result = self.scorer.score(checks)
        self.assertGreaterEqual(result["audit_score"], 0.6)
        self.assertTrue(result["passed"])

    def test_recommendation_present_for_each_failed_check(self):
        checks = self._all_passing_checks()
        checks["hook_check"] = {"passed": False, "score": 0.0}
        result = self.scorer.score(checks)
        self.assertIn("hook_check", result["weaknesses"])
        self.assertIn(AuditScorer.RECOMMENDATION_BY_CHECK["hook_check"], result["recommendations"])

    def test_missing_check_entry_is_treated_as_failed(self):
        checks = {}  # every check missing entirely
        result = self.scorer.score(checks)
        self.assertEqual(result["audit_score"], 0.0)
        self.assertFalse(result["passed"])
        self.assertEqual(set(result["weaknesses"]), set(AuditScorer.WEIGHTS))

    def test_score_never_raises_on_malformed_checks_input(self):
        result = self.scorer.score({"hook_check": "not-a-dict"})
        self.assertEqual(result["audit_score"], 0.0)
        self.assertFalse(result["passed"])
        self.assertTrue(result["recommendations"])

    def test_score_is_clamped_between_zero_and_one(self):
        checks = self._all_passing_checks()
        for name in checks:
            checks[name]["score"] = 5.0  # out-of-range input
        result = self.scorer.score(checks)
        self.assertLessEqual(result["audit_score"], 1.0)

    def test_score_is_deterministic_for_same_input(self):
        checks = self._all_passing_checks()
        result_one = self.scorer.score(dict(checks))
        result_two = self.scorer.score(dict(checks))
        self.assertEqual(result_one, result_two)


if __name__ == "__main__":
    unittest.main()
