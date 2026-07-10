from typing import Any, Dict, List


class PlannerContract(object):
    """
    AI Planner Contract (Sprint 15-0, Architecture Only).

    AI Planner는 앞으로 Pattern Engine / Knowledge Engine / Competitor Engine /
    Image Strategy / Content Engine / Brand DNA Engine / Trend Memory를 조율하는
    중심 Engine이 될 예정이다. 이 Sprint의 목표는 "판단"이 아니라 "계약"이다 -
    입력/출력/Schema/WorkflowEngine 연결 위치만 코드로 확정하고, 실제 Decision
    Engine(판단 로직)은 구현하지 않는다.

    이 클래스는 그 계약을 코드로 남긴 단일 진실 소스(single source of truth)다.
    다른 모듈이나 향후 Sprint, Codex 검수는 이 클래스의 상수/‌`describe()`를
    통해 계약 내용을 확인해야 한다 - 문서(MODULE_STATUS.md 등)와 이 코드가
    어긋나면 이 코드가 기준이다.
    """

    VERSION = "0.1.0-contract-only"

    # AI Planner가 앞으로 조율할 대상 Engine 목록 (docs/AI_PLANNER.md, ROADMAP.md 참고).
    COORDINATED_ENGINES: List[str] = [
        "pattern_engine",
        "knowledge_engine",
        "competitor_engine",
        "image_strategy",
        "content_engine",
        "brand_dna_engine",
        "trend_memory",
    ]

    # Planner Input Contract: PlanningContext(planning_context.py)의 필드와 반드시 일치한다.
    INPUT_FIELDS: List[str] = [
        "trend_result",
        "topic_result",
        "pattern_result",
        "knowledge_result",
        "trend_memory_result",
        "competitor_result",
        "brand_profile",
        "image_strategy_result",
    ]

    # Planner Output Contract: planning_result_schema.py의 REQUIRED_FIELDS와 반드시 일치한다.
    OUTPUT_FIELDS: List[str] = [
        "selected_pattern",
        "selected_hook_strategy",
        "selected_cta_strategy",
        "selected_image_strategy",
        "knowledge_priority",
        "competitor_reference",
        "content_strategy",
        "planner_confidence",
        "planner_reason",
        "planner_version",
    ]

    # WorkflowEngine 연결 위치 (Sprint 15-0에는 주석으로만 표시, 실제 연결 없음).
    WORKFLOW_INTEGRATION_NOTE = (
        "AI Planner는 TopicEngineModule 실행 이후, PatternEngineModule 실행 이전에 "
        "위치할 예정이다 - Pattern/Content/Image Strategy 선택에 영향을 주려면 그 "
        "Engine들이 실행되기 전에 판단 결과가 준비되어 있어야 하기 때문이다. "
        "Sprint 15-0에서는 src/workflow_engine.py에 이 위치를 나타내는 주석만 "
        "추가하며, self.ai_planner_module 인스턴스화나 run() 호출은 추가하지 않는다."
    )

    # 절대 규칙 (Sprint 15-0 한정): 이번 Sprint에서 하지 않는 것.
    NOT_IN_SCOPE_THIS_SPRINT: List[str] = [
        "실제 판단/선택 로직(Decision Engine) 구현",
        "가짜/그럴듯한 기본값으로 채워진 placeholder 결과 생성",
        "WorkflowEngine에 실제 실행 연결(인스턴스화, run() 호출) 추가",
        "storage/planner/에 실행 결과 저장 (History/Score/Storage 클래스 없음)",
    ]

    @classmethod
    def describe(cls) -> Dict[str, Any]:
        """Codex/향후 Sprint가 계약 내용을 코드로 그대로 확인할 수 있게 하는 요약."""
        return {
            "version": cls.VERSION,
            "coordinated_engines": list(cls.COORDINATED_ENGINES),
            "input_fields": list(cls.INPUT_FIELDS),
            "output_fields": list(cls.OUTPUT_FIELDS),
            "workflow_integration_note": cls.WORKFLOW_INTEGRATION_NOTE,
            "not_in_scope_this_sprint": list(cls.NOT_IN_SCOPE_THIS_SPRINT),
        }
