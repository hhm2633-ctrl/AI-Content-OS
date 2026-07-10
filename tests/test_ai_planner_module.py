import unittest

from modules.ai_planner.planner_module import AIPlannerModule
from modules.ai_planner.planning_context import PlanningContext
from modules.ai_planner.planning_result_schema import REQUIRED_FIELDS


class TestAIPlannerModule(unittest.TestCase):
    """
    AIPlannerModule(Sprint 15-1, Decision Engine v1)에 대한 순수 로컬 단위 테스트.

    외부 API/LLM/네트워크를 전혀 사용하지 않는다 - `PlannerInterface`가 내부적으로
    `KnowledgeInterface`/`TrendMemoryInterface`/`CompetitorInterface`/
    `BrandDNAInterface`/`PerformanceScoreInterface`를 생성하지만, 이들은 모두
    로컬 `storage/`만 읽고(파일이 없으면 빈 값), 네트워크/LLM 호출을 하지 않는다.
    `PlannerDecisionEngine`이 실제 판단 로직을 담당하는 세부 테스트는
    `test_ai_planner_decision_engine.py`에 있다 - 여기서는 `AIPlannerModule.run()`이
    그 결과를 올바르게 감싸는지(Output Contract 검증, 예외 안전성, context 정규화)만
    검증한다.
    """

    def setUp(self):
        self.module = AIPlannerModule()

    def _assert_schema_present(self, result):
        for field in REQUIRED_FIELDS:
            self.assertIn(field, result)
        self.assertIn("schema_valid", result)
        self.assertTrue(result["schema_valid"])

    def test_run_with_no_context_returns_schema_valid_result(self):
        result = self.module.run()
        self._assert_schema_present(result)

    def test_run_with_empty_context_returns_schema_valid_result(self):
        result = self.module.run(PlanningContext())
        self._assert_schema_present(result)

    def test_run_delegates_to_decision_engine_for_real_input(self):
        context = PlanningContext(
            trend_result={"trends": [{"keyword": "ChatGPT 자동화", "quality_score": 80}]},
            topic_result={
                "selected_topic": {
                    "keyword": "ChatGPT 자동화",
                    "title": "ChatGPT 자동화 지금 시작해야 하는 이유",
                    "quality_score": 80,
                }
            },
        )

        result = self.module.run(context)
        self._assert_schema_present(result)
        self.assertEqual(result["status"], "planner_decided")
        self.assertEqual(result["selected_pattern"], "tutorial")

    def test_run_never_raises_regardless_of_context_type(self):
        for garbage_context in [
            None,
            PlanningContext(),
            PlanningContext.from_dict(None),
            "not a context",
            12345,
            {"trend_result": {"trends": "not a list"}},
            {"pattern_result": {"should_be_ignored": True}},
        ]:
            try:
                result = self.module.run(garbage_context)
            except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
                self.fail(f"run() raised for context={garbage_context!r}: {error}")

            self._assert_schema_present(result)

    def test_run_coerces_dict_context_via_planning_context_from_dict(self):
        result_from_dict = self.module.run({"topic_result": {"selected_topic": {"keyword": "부업"}}})
        result_from_context = self.module.run(
            PlanningContext(topic_result={"selected_topic": {"keyword": "부업"}})
        )

        self.assertEqual(result_from_dict["selected_pattern"], result_from_context["selected_pattern"])

    def test_interface_is_exposed_for_future_reuse(self):
        self.assertTrue(hasattr(self.module, "interface"))

    def test_decision_engine_is_exposed(self):
        self.assertTrue(hasattr(self.module, "decision_engine"))

    # ---- brand_profile Runtime Input: config-backed, not a prior-stage result ----

    def test_interface_load_brand_profile_never_raises_and_returns_dict(self):
        result = self.module.interface.load_brand_profile()
        self.assertIsInstance(result, dict)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
