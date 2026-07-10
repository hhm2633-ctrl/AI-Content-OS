import unittest

from modules.ai_planner.consumer_contract import MIN_CONFIDENCE_FOR_HINT_APPLICATION
from modules.ai_planner.planner_consumer_adapter import PlannerConsumerAdapter
from modules.ai_planner.planner_interface import PlannerInterface
from modules.pattern_engine.pattern_selector import PatternSelector


def _planner_result(**overrides):
    base = {
        "status": "planner_decided",
        "schema_valid": True,
        "selected_pattern": "tutorial",
        "selected_hook_strategy": "pain_point",
        "selected_cta_strategy": "follow",
        "selected_image_strategy": "ai_tools",
        "knowledge_priority": ["cta", "hook"],
        "competitor_reference": ["some_account"],
        "planner_confidence": 0.8,
    }
    base.update(overrides)
    return base


class TestPlannerConsumerAdapter(unittest.TestCase):
    """
    PlannerConsumerAdapter에 대한 순수 로컬 단위 테스트. 외부 API/LLM/네트워크를
    전혀 사용하지 않는다 - PatternSelector/HookSelector/CTASelector/
    ImageSourceSelector/KnowledgeExtractor는 전부 순수 상수/로컬 계산만 사용한다.

    핵심 불변식: Hint가 거부되는 모든 경우, Engine이 넘긴 기존 값이 "그대로"
    반환되어야 한다 - 기존 Engine의 정상 선택 로직/fallback을 절대 지우거나
    바꾸지 않는다는 CTO 핵심 결정을 검증한다.
    """

    def setUp(self):
        self.adapter = PlannerConsumerAdapter()

    # ---- resolve_pattern ----

    def test_resolve_pattern_applies_hint_when_all_gates_pass(self):
        result = self.adapter.resolve_pattern(
            planner_result=_planner_result(),
            engine_pattern_type="resource",
            topic_confidence_score=0.9,
            blocked=False,
        )
        self.assertEqual(result["pattern_type"], "tutorial")
        self.assertTrue(result["hint_applied"])
        self.assertEqual(result["source"], "planner_hint")

    def test_resolve_pattern_keeps_engine_default_when_confidence_low(self):
        result = self.adapter.resolve_pattern(
            planner_result=_planner_result(planner_confidence=0.1),
            engine_pattern_type="resource",
            topic_confidence_score=0.9,
            blocked=False,
        )
        self.assertEqual(result["pattern_type"], "resource")
        self.assertFalse(result["hint_applied"])
        self.assertEqual(result["source"], "engine_default")

    def test_resolve_pattern_keeps_engine_default_when_blocked(self):
        result = self.adapter.resolve_pattern(
            planner_result=_planner_result(),
            engine_pattern_type="resource",
            topic_confidence_score=0.9,
            blocked=True,
        )
        self.assertEqual(result["pattern_type"], "resource")
        self.assertFalse(result["hint_applied"])

    def test_resolve_pattern_keeps_engine_default_when_topic_confidence_below_safety_threshold(self):
        low_confidence = PatternSelector.LOW_CONFIDENCE_THRESHOLD - 0.01
        result = self.adapter.resolve_pattern(
            planner_result=_planner_result(),
            engine_pattern_type="resource",
            topic_confidence_score=low_confidence,
            blocked=False,
        )
        self.assertEqual(result["pattern_type"], "resource")
        self.assertFalse(result["hint_applied"])

    def test_resolve_pattern_keeps_engine_default_when_hint_value_unsupported(self):
        result = self.adapter.resolve_pattern(
            planner_result=_planner_result(selected_pattern="not_a_real_pattern_type"),
            engine_pattern_type="resource",
            topic_confidence_score=0.9,
            blocked=False,
        )
        self.assertEqual(result["pattern_type"], "resource")
        self.assertFalse(result["hint_applied"])

    def test_resolve_pattern_never_raises_on_garbage_planner_result(self):
        for garbage in [None, "not a dict", 123, {"planner_confidence": object()}]:
            try:
                result = self.adapter.resolve_pattern(
                    planner_result=garbage,
                    engine_pattern_type="resource",
                    topic_confidence_score=0.9,
                    blocked=False,
                )
            except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
                self.fail(f"resolve_pattern raised for {garbage!r}: {error}")

            self.assertEqual(result["pattern_type"], "resource")
            self.assertFalse(result["hint_applied"])

    # ---- resolve_hook / resolve_cta ----

    def test_resolve_hook_applies_hint_when_gates_pass(self):
        result = self.adapter.resolve_hook(
            planner_result=_planner_result(), engine_hook_type="saveable_tip", blocked=False
        )
        self.assertEqual(result["hook_type"], "pain_point")
        self.assertTrue(result["hint_applied"])

    def test_resolve_hook_keeps_engine_default_when_blocked(self):
        result = self.adapter.resolve_hook(
            planner_result=_planner_result(), engine_hook_type="saveable_tip", blocked=True
        )
        self.assertEqual(result["hook_type"], "saveable_tip")
        self.assertFalse(result["hint_applied"])

    def test_resolve_cta_applies_hint_when_gates_pass(self):
        result = self.adapter.resolve_cta(
            planner_result=_planner_result(), engine_cta_type="save", blocked=False
        )
        self.assertEqual(result["cta_type"], "follow")
        self.assertTrue(result["hint_applied"])

    def test_resolve_cta_keeps_engine_default_when_hint_value_unsupported(self):
        result = self.adapter.resolve_cta(
            planner_result=_planner_result(selected_cta_strategy="not_a_real_cta"),
            engine_cta_type="save",
            blocked=False,
        )
        self.assertEqual(result["cta_type"], "save")
        self.assertFalse(result["hint_applied"])

    # ---- resolve_image_strategy ----

    def test_resolve_image_strategy_applies_hint_when_gates_pass(self):
        result = self.adapter.resolve_image_strategy(
            planner_result=_planner_result(), engine_content_type="education"
        )
        self.assertEqual(result["content_type"], "ai_tools")
        self.assertTrue(result["hint_applied"])

    def test_resolve_image_strategy_keeps_engine_default_when_hint_value_unsupported(self):
        result = self.adapter.resolve_image_strategy(
            planner_result=_planner_result(selected_image_strategy="not_a_real_content_type"),
            engine_content_type="education",
        )
        self.assertEqual(result["content_type"], "education")
        self.assertFalse(result["hint_applied"])

    # ---- resolve_knowledge_priority ----

    def test_resolve_knowledge_priority_filters_to_known_types(self):
        result = self.adapter.resolve_knowledge_priority(
            _planner_result(knowledge_priority=["cta", "not_a_real_type", "hook"])
        )
        self.assertTrue(result["hint_applied"])
        self.assertEqual(result["knowledge_priority"], ["cta", "hook"])

    def test_resolve_knowledge_priority_not_applied_when_empty(self):
        result = self.adapter.resolve_knowledge_priority(_planner_result(knowledge_priority=[]))
        self.assertFalse(result["hint_applied"])
        self.assertEqual(result["knowledge_priority"], [])

    def test_resolve_knowledge_priority_preserves_engine_default_on_rejection(self):
        # Codex 검수 반영: 리스트 필드도 scalar 필드와 동일하게, Hint가 거부되면
        # 빈 목록이 아니라 호출측 Engine이 이미 갖고 있던 값을 그대로 반환해야 한다.
        existing_priority = ["brand", "layout"]
        result = self.adapter.resolve_knowledge_priority(
            _planner_result(knowledge_priority=[]), engine_default=existing_priority
        )
        self.assertFalse(result["hint_applied"])
        self.assertEqual(result["knowledge_priority"], existing_priority)
        self.assertEqual(result["source"], "engine_default")

    def test_resolve_knowledge_priority_never_raises_on_garbage(self):
        for garbage in [None, "not a dict", 123]:
            try:
                result = self.adapter.resolve_knowledge_priority(garbage, engine_default=["brand"])
            except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
                self.fail(f"resolve_knowledge_priority raised for {garbage!r}: {error}")

            self.assertFalse(result["hint_applied"])
            self.assertEqual(result["knowledge_priority"], ["brand"])

    # ---- resolve_competitor_reference ----

    def test_resolve_competitor_reference_applies_valid_string_list(self):
        result = self.adapter.resolve_competitor_reference(
            _planner_result(competitor_reference=["acct_a", "acct_b"])
        )
        self.assertTrue(result["hint_applied"])
        self.assertEqual(result["competitor_reference"], ["acct_a", "acct_b"])

    def test_resolve_competitor_reference_not_applied_when_all_blank(self):
        result = self.adapter.resolve_competitor_reference(
            _planner_result(competitor_reference=["  ", ""])
        )
        self.assertFalse(result["hint_applied"])
        self.assertEqual(result["competitor_reference"], [])

    def test_resolve_competitor_reference_preserves_engine_default_on_rejection(self):
        existing_reference = ["existing_account"]
        result = self.adapter.resolve_competitor_reference(
            _planner_result(competitor_reference=["  "]), engine_default=existing_reference
        )
        self.assertFalse(result["hint_applied"])
        self.assertEqual(result["competitor_reference"], existing_reference)
        self.assertEqual(result["source"], "engine_default")

    # ---- 낮은 confidence는 모든 필드에서 일관되게 거부됨 ----

    def test_low_confidence_rejects_hint_across_all_fields(self):
        low_confidence_result = _planner_result(planner_confidence=MIN_CONFIDENCE_FOR_HINT_APPLICATION - 0.01)

        pattern = self.adapter.resolve_pattern(low_confidence_result, "resource", 0.9, False)
        hook = self.adapter.resolve_hook(low_confidence_result, "saveable_tip", False)
        cta = self.adapter.resolve_cta(low_confidence_result, "save", False)
        image_strategy = self.adapter.resolve_image_strategy(low_confidence_result, "education")
        knowledge = self.adapter.resolve_knowledge_priority(low_confidence_result)
        competitor = self.adapter.resolve_competitor_reference(low_confidence_result)

        self.assertFalse(pattern["hint_applied"])
        self.assertFalse(hook["hint_applied"])
        self.assertFalse(cta["hint_applied"])
        self.assertFalse(image_strategy["hint_applied"])
        self.assertFalse(knowledge["hint_applied"])
        self.assertFalse(competitor["hint_applied"])

    # ---- PlannerInterface 연동 ----

    def test_planner_interface_exposes_consumer_adapter(self):
        interface = PlannerInterface()
        adapter = interface.get_consumer_adapter()
        self.assertIsInstance(adapter, PlannerConsumerAdapter)


if __name__ == "__main__":
    unittest.main()
