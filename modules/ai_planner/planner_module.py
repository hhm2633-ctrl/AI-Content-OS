from typing import Any, Dict, Optional

from modules.base_module import BaseModule
from modules.ai_planner.planner_contract import PlannerContract
from modules.ai_planner.planner_interface import PlannerInterface
from modules.ai_planner.planning_context import PlanningContext
from modules.ai_planner.planning_result_schema import build_undecided_result, validate_schema


class AIPlannerModule(BaseModule):
    """
    AI Planner Skeleton (Sprint 15-0, Architecture Only; corrected Sprint 15-0A).

    이 Sprint의 목표는 "판단"이 아니라 "계약"이다. AI Planner v1은 Pre-Planning
    Engine으로 한정되며, `TopicEngineModule` 이후 / `PatternEngineModule` 이전에서
    실행될 예정이다 - Pattern/Knowledge/Trend Memory/Competitor/Image Strategy는
    아직 실행되지 않은 시점이므로, 이 Engine들의 이번 실행 결과는 입력으로 받지
    않는다 (Sprint 15-0A에서 이 구조적 모순을 발견/수정했다).

    이 클래스는 실제 Decision Engine이 아니다:
    - `PlanningContext`(Runtime Input 3개 + Historical Input 5개, 총 8개)를 받는다.
    - `planning_result_schema`의 Output Contract를 그대로 따르는 결과를 만든다.
    - 모든 결정 필드는 명시적으로 비어 있다(None/[]/0.0) - 진짜 판단처럼 보이는
      가짜 값을 채우지 않는다 (Sprint 13 Offline-First 원칙과 동일한 정직성 기준).
      Historical Input에 실제 과거 데이터가 채워져 있어도 이 사실은 변하지 않는다 -
      이 Skeleton은 어떤 입력을 받든 판단을 꾸며내지 않는다.
    - 아무것도 storage에 저장하지 않는다 - History/Score/Storage 클래스가 없다.

    `WorkflowEngine`에는 아직 연결되지 않는다 (`PlannerContract.WORKFLOW_INTEGRATION_NOTE`
    참고) - `src/workflow_engine.py`에는 연결 위치를 나타내는 주석만 추가되어 있고,
    실제 인스턴스화/실행 호출은 없다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}

        # Interface는 향후 Sprint가 재사용할 수 있도록 준비만 해 둔다.
        self.interface = PlannerInterface()

    def run(self, context: Optional[PlanningContext] = None) -> Dict[str, Any]:
        print("AI Planner Module Started (Skeleton - Architecture Only)")

        try:
            result = self._build_undecided_result(context)
        except Exception as error:
            print(f"AI Planner Skeleton Failed, returning safe undecided result: {error}")
            result = build_undecided_result(reason=f"planner_skeleton_exception: {error}")

        print("AI Planner Module Finished (Skeleton - Architecture Only)")
        return result

    def _build_undecided_result(self, context: Optional[PlanningContext]) -> Dict[str, Any]:
        # context는 이번 Sprint에서 실제로 읽히지 않는다 - Contract가 받아들일 수
        # 있음을 보여주기 위해서만 받는다. 실제 판단 로직은 향후 Sprint의 몫이다.
        context = context or PlanningContext()

        result = build_undecided_result(
            reason=(
                "Sprint 15-0은 Architecture 전용 Sprint다 - AI Planner Contract"
                "(입력/출력/Schema/WorkflowEngine 연결 위치)만 확정했으며, "
                f"{', '.join(PlannerContract.COORDINATED_ENGINES)}를 조율하는 "
                "실제 Decision Engine은 아직 구현되지 않았다."
            )
        )

        schema_check = validate_schema(result)
        result["schema_valid"] = schema_check.get("valid", False)

        return result
