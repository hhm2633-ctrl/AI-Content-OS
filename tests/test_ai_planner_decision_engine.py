import unittest

from modules.ai_planner.planner_decision_engine import (
    MIN_BRAND_DNA_OBSERVATIONS_FOR_OVERRIDE,
    PlannerDecisionEngine,
)
from modules.ai_planner.planning_context import PlanningContext
from modules.ai_planner.planning_result_schema import REQUIRED_FIELDS, validate_schema
from modules.pattern_engine.cta_selector import CTASelector
from modules.pattern_engine.hook_selector import HookSelector
from modules.pattern_engine.pattern_selector import PatternSelector

KNOWN_IMAGE_CONTENT_TYPES = {
    "education",
    "tutorial",
    "ai_tools",
    "news",
    "community",
    "shopping",
    "review",
    "promotion",
}


class TestPlannerDecisionEngine(unittest.TestCase):
    """
    PlannerDecisionEngine에 대한 순수 로컬 단위 테스트. 외부 API/LLM/네트워크를
    전혀 사용하지 않는다 - 전부 PlanningContext에 직접 주입한 dict에 대한
    결정론적 규칙 계산만 검증한다.
    """

    def setUp(self):
        self.engine = PlannerDecisionEngine()

    def _assert_valid_decision(self, result):
        for field in REQUIRED_FIELDS:
            self.assertIn(field, result)

        check = validate_schema(result)
        self.assertTrue(check["valid"], check.get("missing_fields"))

        self.assertIn(result["selected_pattern"], PatternSelector.PATTERN_TYPES)
        self.assertIn(result["selected_hook_strategy"], HookSelector.HOOK_TYPES)
        self.assertIn(result["selected_cta_strategy"], CTASelector.CTA_TYPES)
        self.assertIn(result["selected_image_strategy"], KNOWN_IMAGE_CONTENT_TYPES)
        self.assertIsInstance(result["knowledge_priority"], list)
        self.assertIsInstance(result["competitor_reference"], list)
        self.assertIsInstance(result["content_strategy"], str)
        self.assertTrue(result["content_strategy"])
        self.assertIsInstance(result["planner_reason"], str)
        self.assertTrue(result["planner_reason"])
        self.assertGreaterEqual(result["planner_confidence"], 0.0)
        self.assertLessEqual(result["planner_confidence"], 1.0)
        self.assertEqual(result["status"], "planner_decided")

    # ---- 실제 데이터 기반 판단 ----

    def _ai_context(self, **overrides):
        base = dict(
            trend_result={
                "trends": [{"keyword": "ChatGPT 자동화", "quality_score": 80}],
            },
            topic_result={
                "selected_topic": {
                    "keyword": "ChatGPT 자동화",
                    "title": "ChatGPT 자동화 지금 시작해야 하는 이유",
                    "quality_score": 80,
                    "source": "naver_news",
                    "collection_method": "live_collect",
                }
            },
        )
        base.update(overrides)
        return PlanningContext(**base)

    def test_decide_with_realistic_ai_topic_produces_valid_decision(self):
        result = self.engine.decide(self._ai_context())
        self._assert_valid_decision(result)
        self.assertEqual(result["selected_pattern"], "tutorial")
        self.assertEqual(result["selected_image_strategy"], "ai_tools")

    def test_decide_is_deterministic_for_same_input(self):
        context = self._ai_context()
        first = self.engine.decide(context)
        second = self.engine.decide(context)

        first.pop("created_at", None)
        second.pop("created_at", None)
        self.assertEqual(first, second)

    def _assert_undecided(self, result):
        for field in REQUIRED_FIELDS:
            self.assertIn(field, result)

        self.assertIsNone(result["selected_pattern"])
        self.assertIsNone(result["selected_hook_strategy"])
        self.assertIsNone(result["selected_cta_strategy"])
        self.assertIsNone(result["selected_image_strategy"])
        self.assertIsNone(result["content_strategy"])
        self.assertEqual(result["knowledge_priority"], [])
        self.assertEqual(result["competitor_reference"], [])
        self.assertEqual(result["planner_confidence"], 0.0)
        self.assertEqual(result["status"], "planner_not_decided")

    def test_decide_with_none_context_never_raises(self):
        # None -> 빈 PlanningContext로 대체되며, 실제 topic 신호가 전혀 없으므로
        # 그럴듯해 보이는 값을 꾸며내지 않고 정직하게 "판단 보류" 상태를 반환해야 한다.
        result = self.engine.decide(None)
        self._assert_undecided(result)

    def test_decide_with_empty_context_is_honestly_undecided(self):
        # Runtime Input에 실제 topic 신호(title/keyword)가 전혀 없을 때, 각 Selector의
        # 하드코딩된 기본값(number_list/saveable_tip/save 등)을 흉내내는 대신 정직하게
        # 미결정 상태를 반환한다 - "실제 신호 없이 그럴듯한 값을 반환하지 않는다"는
        # Codex 검수 지적을 반영한 회귀 테스트다.
        result = self.engine.decide(PlanningContext())
        self._assert_undecided(result)

    def test_decide_with_non_dict_selected_topic_is_honestly_undecided(self):
        context = self._ai_context(topic_result={"selected_topic": "not_a_dict"})
        result = self.engine.decide(context)
        self._assert_undecided(result)

    def test_decide_with_blank_selected_topic_fields_is_honestly_undecided(self):
        context = self._ai_context(
            topic_result={"selected_topic": {"title": "  ", "keyword": ""}}
        )
        result = self.engine.decide(context)
        self._assert_undecided(result)

    # ---- Brand DNA 이력 기반 hook/cta override ----

    def test_brand_dna_override_applied_with_sufficient_observations(self):
        context = self._ai_context(
            brand_dna_history={
                "dominant_hook_type": "authority",
                "dominant_cta_type": "profile",
                "total_observations": MIN_BRAND_DNA_OBSERVATIONS_FOR_OVERRIDE,
            }
        )
        baseline = self.engine.decide(self._ai_context())
        result = self.engine.decide(context)

        self.assertNotEqual(baseline["selected_hook_strategy"], "authority")
        self.assertNotEqual(baseline["selected_cta_strategy"], "profile")
        self.assertEqual(result["selected_hook_strategy"], "authority")
        self.assertEqual(result["selected_cta_strategy"], "profile")
        self.assertTrue(result["decision_basis"]["brand_dna_hook_override_used"])
        self.assertTrue(result["decision_basis"]["brand_dna_cta_override_used"])

    def test_brand_dna_override_not_applied_with_insufficient_observations(self):
        context = self._ai_context(
            brand_dna_history={
                "dominant_hook_type": "authority",
                "dominant_cta_type": "follow",
                "total_observations": MIN_BRAND_DNA_OBSERVATIONS_FOR_OVERRIDE - 1,
            }
        )
        baseline = self.engine.decide(self._ai_context())
        result = self.engine.decide(context)

        self.assertEqual(result["selected_hook_strategy"], baseline["selected_hook_strategy"])
        self.assertEqual(result["selected_cta_strategy"], baseline["selected_cta_strategy"])
        self.assertFalse(result["decision_basis"]["brand_dna_hook_override_used"])
        self.assertFalse(result["decision_basis"]["brand_dna_cta_override_used"])

    def test_brand_dna_override_ignored_if_dominant_value_invalid(self):
        context = self._ai_context(
            brand_dna_history={
                "dominant_hook_type": "not_a_real_hook_type",
                "dominant_cta_type": "not_a_real_cta_type",
                "total_observations": 999,
            }
        )
        baseline = self.engine.decide(self._ai_context())
        result = self.engine.decide(context)

        self.assertEqual(result["selected_hook_strategy"], baseline["selected_hook_strategy"])
        self.assertEqual(result["selected_cta_strategy"], baseline["selected_cta_strategy"])
        self.assertFalse(result["decision_basis"]["brand_dna_hook_override_used"])
        self.assertFalse(result["decision_basis"]["brand_dna_cta_override_used"])

    # ---- knowledge_priority ----

    def test_knowledge_priority_ranks_by_score_descending(self):
        context = self._ai_context(
            knowledge_history={
                "average_overall_score_by_type": {"hook": 0.5, "cta": 0.9, "pattern": 0.7}
            }
        )
        result = self.engine.decide(context)
        self.assertEqual(result["knowledge_priority"], ["cta", "pattern", "hook"])

    def test_knowledge_priority_empty_when_scores_missing(self):
        context = self._ai_context(knowledge_history={"total_runs": 5})
        result = self.engine.decide(context)
        self.assertEqual(result["knowledge_priority"], [])

    def test_knowledge_priority_ignores_non_numeric_scores(self):
        context = self._ai_context(
            knowledge_history={
                "average_overall_score_by_type": {"hook": "not_a_number", "cta": 0.9}
            }
        )
        result = self.engine.decide(context)
        self.assertEqual(result["knowledge_priority"], ["cta"])

    # ---- competitor_reference ----

    def test_competitor_reference_filters_and_orders_by_priority(self):
        context = self._ai_context(
            competitor_history={
                "account_profiles": [
                    {"account": "low_priority_acct", "priority": "Medium"},
                    {"account": "high_acct", "priority": "High"},
                    {"account": "very_high_acct", "priority": "Very High"},
                    {"account": "no_priority_acct"},
                ]
            }
        )
        result = self.engine.decide(context)
        self.assertEqual(result["competitor_reference"], ["very_high_acct", "high_acct"])

    def test_competitor_reference_empty_when_no_eligible_profiles(self):
        context = self._ai_context(
            competitor_history={"account_profiles": [{"account": "low", "priority": "Low"}]}
        )
        result = self.engine.decide(context)
        self.assertEqual(result["competitor_reference"], [])

    # ---- 방어적 처리: 손상된 Historical Input이 예외를 일으키지 않음 ----

    def test_decide_never_raises_on_malformed_historical_data(self):
        # 각 케이스는 실제 selected_topic(title 존재)은 그대로 두고, Historical Input만
        # 손상시킨다 - 그래야 "topic 신호 없음" 분기가 아니라 실제로 Historical Input
        # 방어 로직을 검증하게 된다.
        malformed_contexts = [
            self._ai_context(knowledge_history={"average_overall_score_by_type": ["not", "a", "dict"]}),
            self._ai_context(competitor_history={"account_profiles": "not_a_list"}),
            self._ai_context(competitor_history={"account_profiles": [{"account": None, "priority": "High"}]}),
            self._ai_context(brand_dna_history={"total_observations": "not_a_number"}),
            self._ai_context(trend_result={"trends": "not_a_list"}),
        ]

        for context in malformed_contexts:
            try:
                result = self.engine.decide(context)
            except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
                self.fail(f"decide() raised for malformed context: {error}")

            self._assert_valid_decision(result)

    # ---- 미래 단계 결과를 입력으로 쓰지 않음 (Sprint 15-0A 회귀 방지) ----

    def test_decide_does_not_depend_on_forbidden_future_stage_attributes(self):
        context = self._ai_context()
        for forbidden_attr in (
            "pattern_result",
            "knowledge_result",
            "trend_memory_result",
            "competitor_result",
            "image_strategy_result",
        ):
            self.assertFalse(hasattr(context, forbidden_attr))

        # PlanningContext에 애초에 그 필드가 없으므로, decide()가 정상 동작하는 것
        # 자체가 이 필드들에 의존하지 않는다는 증거다.
        result = self.engine.decide(context)
        self._assert_valid_decision(result)


if __name__ == "__main__":
    unittest.main()
