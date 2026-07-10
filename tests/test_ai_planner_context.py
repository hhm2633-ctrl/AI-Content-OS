import unittest

from modules.ai_planner.planner_contract import PlannerContract
from modules.ai_planner.planning_context import PlanningContext


class TestPlanningContext(unittest.TestCase):
    """
    PlanningContext에 대한 순수 로컬 단위 테스트. 외부 API/LLM/네트워크를 전혀
    사용하지 않는다.
    """

    def test_default_construction_has_all_fields_as_empty_dict(self):
        context = PlanningContext()
        data = context.to_dict()

        self.assertEqual(set(data.keys()), set(PlannerContract.INPUT_FIELDS))
        for field, value in data.items():
            self.assertEqual(value, {}, f"{field} should default to an empty dict")

    def test_runtime_fields_accept_real_values(self):
        context = PlanningContext(
            trend_result={"status": "success"},
            topic_result={"selected_topic": {"title": "t"}},
            brand_profile={"brand_name": "AI-Content-OS"},
        )

        self.assertEqual(context.trend_result, {"status": "success"})
        self.assertEqual(context.topic_result, {"selected_topic": {"title": "t"}})
        self.assertEqual(context.brand_profile, {"brand_name": "AI-Content-OS"})

        # 나머지 5개 Historical Input은 지정하지 않았으므로 빈 dict여야 한다.
        for field in PlannerContract.HISTORICAL_INPUT_FIELDS:
            self.assertEqual(getattr(context, field), {})

    def test_historical_fields_accept_real_values(self):
        context = PlanningContext(
            knowledge_history={"total_runs": 5},
            trend_memory_history={"recent": []},
            competitor_history={"account_profiles": []},
            brand_dna_history={"dominant_hook_type": "saveable_tip"},
            performance_history={"average": {}},
        )

        self.assertEqual(context.knowledge_history, {"total_runs": 5})
        self.assertEqual(context.trend_memory_history, {"recent": []})
        self.assertEqual(context.competitor_history, {"account_profiles": []})
        self.assertEqual(context.brand_dna_history, {"dominant_hook_type": "saveable_tip"})
        self.assertEqual(context.performance_history, {"average": {}})

    def test_to_dict_from_dict_round_trip(self):
        original = PlanningContext(
            trend_result={"a": 1},
            topic_result={"b": 2},
            brand_profile={"c": 3},
            knowledge_history={"d": 4},
            trend_memory_history={"e": 5},
            competitor_history={"f": 6},
            brand_dna_history={"g": 7},
            performance_history={"h": 8},
        )

        rebuilt = PlanningContext.from_dict(original.to_dict())

        self.assertEqual(rebuilt.to_dict(), original.to_dict())

    # ---- 요구사항 8: PlanningContext.from_dict가 잘못된 입력에서도 예외 없음 ----

    def test_from_dict_never_raises_on_invalid_input(self):
        for garbage in [None, 123, ["a", "b"], "just a string", object(), {}]:
            try:
                context = PlanningContext.from_dict(garbage)
            except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
                self.fail(f"from_dict() raised an exception for {garbage!r}: {error}")

            self.assertIsInstance(context, PlanningContext)
            self.assertEqual(set(context.to_dict().keys()), set(PlannerContract.INPUT_FIELDS))

    def test_from_dict_ignores_unknown_and_forbidden_keys(self):
        # pattern_result 등 미래 단계 결과가 dict에 섞여 들어와도 무시되어야 한다
        # (PlanningContext 생성자가 애초에 그런 키워드 인자를 받지 않는다).
        data = {
            "trend_result": {"ok": True},
            "pattern_result": {"should_be_ignored": True},
            "image_strategy_result": {"should_be_ignored": True},
            "unknown_field": "should also be ignored",
        }

        context = PlanningContext.from_dict(data)

        self.assertEqual(context.trend_result, {"ok": True})
        self.assertFalse(hasattr(context, "pattern_result"))
        self.assertFalse(hasattr(context, "image_strategy_result"))
        self.assertFalse(hasattr(context, "unknown_field"))


if __name__ == "__main__":
    unittest.main()
