import unittest

from modules.content.content_prompt_builder import ContentPromptBuilder


class _NoCompetitorHints:
    def get_top_hooks(self, limit=3):
        return []

    def get_top_ctas(self, limit=3):
        return []


class TestContentPromptBuilderContract(unittest.TestCase):
    def setUp(self):
        self.builder = ContentPromptBuilder()
        self.builder.competitor_learning_interface = _NoCompetitorHints()
        self.research_result = {
            "keyword": "AI 업무 자동화",
            "title": "반복 업무를 줄이는 AI 자동화",
            "summary": "작은 반복 업무부터 자동화하는 방법",
            "key_points": ["작게 시작", "결과 검수"],
            "target": "AI 자동화 초보자",
            "topic_angle": "과장 없이 바로 적용 가능한 순서",
            "pattern_plan": {
                "pattern_type": "tutorial",
                "layout_type": "bold_ai",
                "reason": "단계별 설명이 필요한 주제",
                "fallback_used": False,
            },
            "topic_intelligence": {
                "category": "AI",
                "cluster": "automation",
                "confidence_score": 0.8,
                "keywords": ["AI", "자동화"],
                "blocked": False,
            },
        }

    def _planner_result(self, confidence=0.9, content_strategy="사례를 먼저 보여주고 절차를 설명"):
        return {
            "status": "planner_decided",
            "schema_valid": True,
            "planner_confidence": confidence,
            "selected_hook_strategy": "contrarian",
            "selected_cta_strategy": "comment",
            "content_strategy": content_strategy,
        }

    def test_missing_pattern_plan_returns_none_for_legacy_fallback(self):
        self.assertIsNone(self.builder.build({"keyword": "AI"}))
        self.assertIsNone(self.builder.build({"pattern_plan": "invalid"}))
        self.assertIsNone(self.builder.build({"pattern_plan": {"pattern_type": ""}}))

    def test_build_surfaces_research_context_and_four_slide_contract(self):
        result = self.builder.build(self.research_result)

        self.assertIsNotNone(result)
        prompt = result["user_prompt"]
        for expected in (
            "AI 업무 자동화",
            "반복 업무를 줄이는 AI 자동화",
            "작은 반복 업무부터 자동화하는 방법",
            "AI 자동화 초보자",
            "과장 없이 바로 적용 가능한 순서",
            '"page": 4',
            '"status": "content_created"',
        ):
            self.assertIn(expected, prompt)

    def test_meta_contract_records_prompt_and_selection_provenance(self):
        result = self.builder.build(self.research_result)
        meta = result["meta"]

        for key in (
            "pattern_type",
            "hook_type",
            "hook_score",
            "cta_type",
            "cta_score",
            "layout_type",
            "prompt_source",
            "pattern_fallback_used",
            "planner_consumption",
            "competitor_learning_consumption",
        ):
            self.assertIn(key, meta)
        self.assertFalse(meta["pattern_fallback_used"])
        self.assertFalse(meta["planner_consumption"]["hook"]["planner_applied"])

    def test_valid_planner_content_strategy_is_advisory_and_recorded(self):
        strategy = "사례를 먼저 보여주고 절차를 설명"
        result = self.builder.build(self.research_result, self._planner_result(content_strategy=strategy))

        self.assertIn(f"AI Planner 참고 전략(강제 아님, 참고만): {strategy}", result["system_prompt"])
        consumption = result["meta"]["planner_consumption"]["content_strategy"]
        self.assertTrue(consumption["planner_applied"])
        self.assertEqual(consumption["final_value"], strategy)

    def test_low_confidence_or_blank_strategy_is_not_injected(self):
        for planner in (
            self._planner_result(confidence=0.1),
            self._planner_result(content_strategy="   "),
            {"status": "planner_fallback", "schema_valid": False, "content_strategy": "강제 전략"},
        ):
            with self.subTest(planner=planner):
                result = self.builder.build(self.research_result, planner)
                self.assertNotIn("AI Planner 참고 전략(강제 아님, 참고만):", result["system_prompt"])
                self.assertFalse(
                    result["meta"]["planner_consumption"]["content_strategy"]["planner_applied"]
                )

    def test_brand_profile_rules_are_present_in_system_prompt(self):
        self.builder.brand_profile = {
            "brand_name": "Test Brand",
            "voice": "명확하고 차분한 말투",
            "target_audience": "초보 운영자",
            "banned_words": ["무조건", "확정 수익"],
        }

        result = self.builder.build(self.research_result)

        self.assertIn("브랜드: Test Brand", result["system_prompt"])
        self.assertIn("다음 표현은 피한다: 무조건, 확정 수익", result["system_prompt"])

    def test_malformed_research_shapes_never_raise(self):
        for value in (None, "invalid", 123, [], {"pattern_plan": []}):
            with self.subTest(value=value):
                try:
                    result = self.builder.build(value)
                except Exception as error:  # pragma: no cover
                    self.fail(f"build raised for malformed input {value!r}: {error}")
                self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
