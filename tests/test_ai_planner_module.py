import unittest

from modules.ai_planner.planner_module import AIPlannerModule
from modules.ai_planner.planning_context import PlanningContext
from modules.ai_planner.planning_result_schema import REQUIRED_FIELDS


class TestAIPlannerModule(unittest.TestCase):
    """
    AIPlannerModule(Skeleton)에 대한 순수 로컬 단위 테스트.

    외부 API/LLM/네트워크를 전혀 사용하지 않는다 - `PlannerInterface`가 내부적으로
    `KnowledgeInterface`/`TrendMemoryInterface`/`CompetitorInterface`/
    `BrandDNAInterface`/`PerformanceScoreInterface`를 생성하지만, 이들은 모두
    로컬 `storage/`만 읽고(파일이 없으면 빈 값), 네트워크/LLM 호출을 하지 않는다.
    """

    def setUp(self):
        self.module = AIPlannerModule()

    def _assert_fully_undecided(self, result):
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
        self.assertTrue(result.get("schema_valid"))

    # ---- 요구사항 9: 입력값과 관계없이 판단을 꾸며내지 않음 ----

    def test_run_with_no_context_is_fully_undecided(self):
        result = self.module.run()
        self._assert_fully_undecided(result)

    def test_run_with_empty_context_is_fully_undecided(self):
        result = self.module.run(PlanningContext())
        self._assert_fully_undecided(result)

    def test_run_with_populated_runtime_inputs_still_undecided(self):
        context = PlanningContext(
            trend_result={"status": "success", "trends": [{"title": "hot topic"}]},
            topic_result={"selected_topic": {"title": "hot topic", "quality_score": 90}},
            brand_profile={"brand_name": "AI-Content-OS", "tone_keywords": ["신뢰감"]},
        )

        result = self.module.run(context)
        self._assert_fully_undecided(result)

    def test_run_with_populated_historical_inputs_still_undecided(self):
        # 실제로 값이 꽉 찬 과거 이력을 넣어도(가짜가 아니라 그럴듯한 실제 형태의
        # 데이터) Skeleton은 여전히 아무것도 판단하지 않아야 한다.
        context = PlanningContext(
            knowledge_history={"total_runs": 20, "by_type": {"hook": 20, "cta": 20}},
            trend_memory_history={"recent": [{"topic_title": "old topic", "hook_type": "saveable_tip"}]},
            competitor_history={"account_profiles": [{"account": "example", "priority": "High"}]},
            brand_dna_history={"dominant_hook_type": "saveable_tip", "dominant_cta_type": "save"},
            performance_history={"average": {"overall_performance_score": 0.85}},
        )

        result = self.module.run(context)
        self._assert_fully_undecided(result)

    def test_run_with_fully_populated_context_still_undecided(self):
        context = PlanningContext(
            trend_result={"status": "success"},
            topic_result={"selected_topic": {"title": "t"}},
            brand_profile={"brand_name": "AI-Content-OS"},
            knowledge_history={"total_runs": 20},
            trend_memory_history={"recent": []},
            competitor_history={"account_profiles": []},
            brand_dna_history={"dominant_hook_type": "saveable_tip"},
            performance_history={"average": {}},
        )

        result = self.module.run(context)
        self._assert_fully_undecided(result)

    def test_run_never_raises_regardless_of_context(self):
        for garbage_context in [None, PlanningContext(), PlanningContext.from_dict(None)]:
            try:
                result = self.module.run(garbage_context)
            except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
                self.fail(f"run() raised for context={garbage_context!r}: {error}")

            self._assert_fully_undecided(result)

    def test_interface_is_exposed_for_future_reuse(self):
        self.assertTrue(hasattr(self.module, "interface"))

    # ---- brand_profile Runtime Input: config-backed, not a prior-stage result ----

    def test_interface_load_brand_profile_never_raises_and_returns_dict(self):
        result = self.module.interface.load_brand_profile()
        self.assertIsInstance(result, dict)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
