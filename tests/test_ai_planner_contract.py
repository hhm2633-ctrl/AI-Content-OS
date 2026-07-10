import unittest
from pathlib import Path

from modules.ai_planner.planner_contract import PlannerContract
from modules.ai_planner.planning_context import PlanningContext
from modules.ai_planner.planning_result_schema import REQUIRED_FIELDS

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ENGINE_PATH = REPO_ROOT / "src" / "workflow_engine.py"

# Sprint 15-0에서 실제로 아직 존재하지 않는 미래 단계 결과를 Planner Input으로
# 요구했던 구조적 결함 - Sprint 15-0A에서 제거되었는지 회귀 검증한다.
FUTURE_STAGE_RESULT_NAMES = [
    "pattern_result",
    "knowledge_result",
    "trend_memory_result",
    "competitor_result",
    "image_strategy_result",
]


class TestPlannerContract(unittest.TestCase):
    """
    ContentModule 테스트와 동일하게 외부 API/LLM/네트워크를 전혀 사용하지 않는다 -
    PlannerContract 상수와 PlanningContext/planning_result_schema, 그리고
    src/workflow_engine.py의 실제 소스 텍스트만 검사한다.
    """

    # ---- 요구사항 1: Runtime Input이 Planner 실행 위치 이전 값만 포함 ----

    def test_runtime_input_fields_are_pre_planner_values_only(self):
        self.assertEqual(
            PlannerContract.RUNTIME_INPUT_FIELDS,
            ["trend_result", "topic_result", "brand_profile"],
        )
        for forbidden in FUTURE_STAGE_RESULT_NAMES:
            self.assertNotIn(forbidden, PlannerContract.RUNTIME_INPUT_FIELDS)

    # ---- 요구사항 2: Historical Input이 과거 저장 데이터로 명확히 구분됨 ----

    def test_historical_input_fields_are_suffixed_with_history(self):
        self.assertEqual(
            PlannerContract.HISTORICAL_INPUT_FIELDS,
            [
                "knowledge_history",
                "trend_memory_history",
                "competitor_history",
                "brand_dna_history",
                "performance_history",
            ],
        )
        for field in PlannerContract.HISTORICAL_INPUT_FIELDS:
            self.assertTrue(field.endswith("_history"), f"{field} should end with _history")
            self.assertFalse(field.endswith("_result"), f"{field} should not look like a current-run result")

    # ---- 요구사항 3: PlannerContract.INPUT_FIELDS와 PlanningContext 필드 일치 ----

    def test_input_fields_is_exact_concat_of_runtime_and_historical(self):
        self.assertEqual(
            PlannerContract.INPUT_FIELDS,
            PlannerContract.RUNTIME_INPUT_FIELDS + PlannerContract.HISTORICAL_INPUT_FIELDS,
        )

    def test_input_fields_match_planning_context_fields_exactly(self):
        context_fields = set(PlanningContext().to_dict().keys())
        self.assertEqual(context_fields, set(PlannerContract.INPUT_FIELDS))

    # ---- 요구사항 4/5: 현재 실행의 미래 단계 결과가 입력에 없음 ----

    def test_pattern_result_not_in_input_fields(self):
        self.assertNotIn("pattern_result", PlannerContract.INPUT_FIELDS)
        self.assertFalse(hasattr(PlanningContext(), "pattern_result"))

    def test_image_strategy_result_not_in_input_fields(self):
        self.assertNotIn("image_strategy_result", PlannerContract.INPUT_FIELDS)
        self.assertFalse(hasattr(PlanningContext(), "image_strategy_result"))

    def test_all_future_stage_result_names_excluded(self):
        for forbidden in FUTURE_STAGE_RESULT_NAMES:
            self.assertNotIn(forbidden, PlannerContract.INPUT_FIELDS)
            self.assertIn(forbidden, PlannerContract.FORBIDDEN_FUTURE_STAGE_INPUT_FIELDS)
            self.assertFalse(hasattr(PlanningContext(), forbidden))

    # ---- Output Contract 일관성 ----

    def test_output_fields_match_schema_required_fields(self):
        self.assertEqual(PlannerContract.OUTPUT_FIELDS, REQUIRED_FIELDS)

    # ---- 요구사항 10: WorkflowEngine에 실제 import/인스턴스/run 호출이 없음 ----

    def test_workflow_engine_has_no_real_ai_planner_wiring(self):
        source = WORKFLOW_ENGINE_PATH.read_text(encoding="utf-8")

        code_only_lines = [
            line for line in source.splitlines()
            if not line.strip().startswith("#")
        ]
        code_only = "\n".join(code_only_lines)

        self.assertNotIn("import AIPlannerModule", code_only)
        self.assertNotIn("from modules.ai_planner", code_only)
        self.assertNotIn("AIPlannerModule(", code_only)
        self.assertNotIn(".ai_planner_module.run(", code_only)

        # 주석 자체는 존재해야 한다 (연결 위치 표시) - 주석까지 사라지면 안 된다.
        self.assertIn("AI Planner", source)
        self.assertIn("Architecture Only", source)

    def test_describe_exposes_full_contract(self):
        described = PlannerContract.describe()

        for key in (
            "version", "coordinated_engines", "runtime_input_fields",
            "historical_input_fields", "input_fields",
            "forbidden_future_stage_input_fields", "output_fields",
            "workflow_integration_note", "not_in_scope_this_sprint",
        ):
            self.assertIn(key, described)

        self.assertEqual(described["runtime_input_fields"], PlannerContract.RUNTIME_INPUT_FIELDS)
        self.assertEqual(described["historical_input_fields"], PlannerContract.HISTORICAL_INPUT_FIELDS)


if __name__ == "__main__":
    unittest.main()
