from typing import Any, Dict, Optional

from modules.base_module import BaseModule
from modules.ai_planner.planner_decision_engine import PlannerDecisionEngine
from modules.ai_planner.planner_interface import PlannerInterface
from modules.ai_planner.planning_context import PlanningContext
from modules.ai_planner.planning_result_schema import build_undecided_result, validate_schema


class AIPlannerModule(BaseModule):
    """
    AI Planner - Decision Engine v1 (Sprint 15-1).

    Sprint 15-0/15-0A는 Contract만 정의하는 Architecture-only Sprint였다 - 이
    클래스는 항상 `build_undecided_result()`(전부 None/[]/0.0)를 반환하는
    Skeleton이었다. Sprint 15-1부터는 `PlannerDecisionEngine`을 실제로 호출해
    콘텐츠 전략을 결정한다:

    - `PlanningContext`(Runtime Input 3개 + Historical Input 5개)를 받는다.
    - 판단 로직 자체는 이 클래스가 아니라 `planner_decision_engine.py::PlannerDecisionEngine`에
      있다 - 이 클래스는 그 결과를 `planning_result_schema`의 Output Contract로
      검증(`validate_schema`)해 반환하는 얇은 진입점이다.
    - Decision Engine은 LLM/외부 API를 쓰지 않는다 - `PatternEngineModule`이 실제로
      쓰는 것과 동일한 규칙 기반 클래스(KeywordWeightEngine/TopicClassifier/
      TopicCluster/ConfidenceScorer/PatternSelector/HookSelector/CTASelector)를
      재사용하고, 나머지는 로컬 storage에 실제로 누적된 Historical Input을
      정렬/필터링한 결과다. 어떤 계산이 실패해도 예외를 던지지 않고
      `build_undecided_result()`(정직한 "판단 실패" 상태)로 안전하게 대체된다.

    `WorkflowEngine`에는 여전히 연결되지 않는다 (Sprint 15-1의 명시적 범위 제한:
    "아직 WorkflowEngine에는 실제 연결하지 않는다") - `src/workflow_engine.py`에는
    연결 위치를 나타내는 주석만 있고, 실제 인스턴스화/실행 호출은 없다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}

        # Interface는 향후 Sprint(WorkflowEngine 실제 연결)가 재사용할 수 있도록 준비만 해 둔다.
        self.interface = PlannerInterface()
        self.decision_engine = PlannerDecisionEngine(self.config)

    def run(self, context: Optional[Any] = None) -> Dict[str, Any]:
        print("AI Planner Module Started (Decision Engine v1)")

        context = self._coerce_context(context)

        try:
            result = self.decision_engine.decide(context)
        except Exception as error:
            print(f"AI Planner Decision Engine Failed, returning safe undecided result: {error}")
            result = build_undecided_result(reason=f"planner_module_exception: {error}")

        schema_check = validate_schema(result)
        result["schema_valid"] = schema_check.get("valid", False)

        print("AI Planner Module Finished (Decision Engine v1)")
        return result

    def _coerce_context(self, context: Optional[Any]) -> PlanningContext:
        """
        `run()`이 어떤 타입을 받아도 절대 예외를 던지지 않도록 방어적으로
        `PlanningContext`로 정규화한다 - `PlanningContext.from_dict()`와 동일한
        "무엇을 받아도 안전한 기본값" 계약을 여기서도 그대로 지킨다.
        """
        if isinstance(context, PlanningContext):
            return context

        if isinstance(context, dict):
            return PlanningContext.from_dict(context)

        return PlanningContext()
