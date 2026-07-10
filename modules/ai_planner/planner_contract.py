from typing import Any, Dict, List


class PlannerContract(object):
    """
    AI Planner Contract (Sprint 15-0, Architecture Only; corrected Sprint 15-0A).

    AI Planner v1 is scoped as a **Pre-Planning Engine** for the current run's
    initial strategy - not a coordinator that waits for stages that haven't run
    yet. Sprint 15-0 originally placed it between TopicEngineModule and
    PatternEngineModule, but its `PlanningContext` required current-run results
    (`pattern_result`, `knowledge_result`, `trend_memory_result`,
    `competitor_result`, `image_strategy_result`) that do not exist yet at that
    point in `WorkflowEngine.run()` - a structural contradiction found and fixed
    in Sprint 15-0A.

    The fix: split inputs into two kinds.

    - **Runtime Inputs** - values that genuinely exist at the Planner's real
      execution position (`trend_result`, `topic_result`, `brand_profile`).
      `trend_result`/`topic_result` come from the prior `WorkflowEngine`
      stages' actual results; `brand_profile` comes from static configuration
      (`config/brand_profile.json` via `BrandProfileLoader`, see
      `planner_interface.py::PlannerInterface.load_brand_profile()`) rather
      than a prior stage's output - it is a Runtime Input because it is
      unconditionally available at this position, not because a stage
      produced it.
    - **Historical Inputs** - accumulated data already persisted to local
      storage by *other* Engines' *past* runs (`knowledge_history`,
      `trend_memory_history`, `competitor_history`, `brand_dna_history`,
      `performance_history`). These are never the current run's not-yet-produced
      results - they are read from disk via each Engine's existing Interface
      (see `planner_interface.py::PlannerInterface.load_historical_inputs()`).

    This class remains the single source of truth for the contract. If
    documentation (MODULE_STATUS.md etc.) disagrees with this code, this code
    is authoritative.
    """

    VERSION = "0.2.0-contract-only"

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

    # Runtime Inputs: 실제 Planner 실행 위치(TopicEngineModule 이후, PatternEngineModule
    # 이전)에서 이미 존재하는 현재 실행 값만 포함한다.
    RUNTIME_INPUT_FIELDS: List[str] = [
        "trend_result",
        "topic_result",
        "brand_profile",
    ]

    # Historical Inputs: 로컬 저장소에 누적된 "과거" 데이터만 포함한다. 이번 실행에서
    # 아직 만들어지지 않은 미래 단계 결과(*_result)는 여기 포함되지 않는다 - 이름 자체를
    # `*_history`로 명확히 구분해 혼동을 막는다.
    HISTORICAL_INPUT_FIELDS: List[str] = [
        "knowledge_history",
        "trend_memory_history",
        "competitor_history",
        "brand_dna_history",
        "performance_history",
    ]

    # Planner Input Contract: PlanningContext(planning_context.py)의 필드와 반드시 일치한다.
    # RUNTIME_INPUT_FIELDS + HISTORICAL_INPUT_FIELDS의 단순 합이다 (임의로 재정의하지 않음).
    INPUT_FIELDS: List[str] = RUNTIME_INPUT_FIELDS + HISTORICAL_INPUT_FIELDS

    # 이번 실행에서 아직 생성되지 않으므로 Planner Input으로 절대 받지 않는 필드.
    # (Sprint 15-0A에서 발견된 구조적 결함 - 실수로 다시 추가되지 않도록 명시적으로 금지 목록화.)
    FORBIDDEN_FUTURE_STAGE_INPUT_FIELDS: List[str] = [
        "pattern_result",
        "knowledge_result",
        "trend_memory_result",
        "competitor_result",
        "image_strategy_result",
    ]

    # Planner Output Contract: planning_result_schema.py의 REQUIRED_FIELDS와 반드시 일치한다.
    # 각 필드는 "이번 실행의 미래 결과를 흉내내는 값"이 아니라 하위 Engine에 전달할
    # 계획/힌트 값이어야 한다 (planning_result_schema.TARGET_ENGINE_BY_FIELD 참고).
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

    # WorkflowEngine 연결 위치 (Sprint 15-0A로 수정: TrendCollectorModule 다음이 아니라
    # TopicEngineModule 다음, PatternEngineModule 이전. 실제로는 여전히 주석으로만 표시).
    WORKFLOW_INTEGRATION_NOTE = (
        "AI Planner v1은 Pre-Planning Engine으로 한정한다. 실행 위치: "
        "TrendCollectorModule -> TopicEngineModule -> AIPlannerModule -> "
        "PatternEngineModule. Sprint 15-0에서는 Planner가 이 위치에서 아직 존재하지 "
        "않는 미래 단계 결과(pattern_result/knowledge_result/trend_memory_result/"
        "competitor_result/image_strategy_result)를 입력으로 요구하는 구조적 모순이 "
        "있었다 (Sprint 15-0A에서 발견 및 수정). 이제 Runtime Input은 이 위치에서 "
        "실제로 존재하는 trend_result/topic_result/brand_profile만 사용하고, "
        "Pattern/Knowledge/Trend Memory/Competitor/Image Strategy에 대한 참고는 "
        "이번 실행 결과가 아니라 storage/에 누적된 과거 이력만 사용한다. "
        "src/workflow_engine.py에는 이 위치를 나타내는 주석만 있으며, "
        "self.ai_planner_module 인스턴스화나 run() 호출은 추가하지 않는다."
    )

    # 절대 규칙 (Sprint 15-0/15-0A 한정): 이번 Sprint에서 하지 않는 것.
    NOT_IN_SCOPE_THIS_SPRINT: List[str] = [
        "실제 판단/선택 로직(Decision Engine) 구현",
        "가짜/그럴듯한 기본값으로 채워진 placeholder 결과 생성",
        "WorkflowEngine에 실제 실행 연결(인스턴스화, run() 호출) 추가",
        "storage/planner/에 실행 결과 저장 (History/Score/Storage 클래스 없음)",
        "이번 실행에서 아직 생성되지 않은 미래 단계 결과를 Planner Input으로 사용",
    ]

    @classmethod
    def describe(cls) -> Dict[str, Any]:
        """Codex/향후 Sprint가 계약 내용을 코드로 그대로 확인할 수 있게 하는 요약."""
        return {
            "version": cls.VERSION,
            "coordinated_engines": list(cls.COORDINATED_ENGINES),
            "runtime_input_fields": list(cls.RUNTIME_INPUT_FIELDS),
            "historical_input_fields": list(cls.HISTORICAL_INPUT_FIELDS),
            "input_fields": list(cls.INPUT_FIELDS),
            "forbidden_future_stage_input_fields": list(cls.FORBIDDEN_FUTURE_STAGE_INPUT_FIELDS),
            "output_fields": list(cls.OUTPUT_FIELDS),
            "workflow_integration_note": cls.WORKFLOW_INTEGRATION_NOTE,
            "not_in_scope_this_sprint": list(cls.NOT_IN_SCOPE_THIS_SPRINT),
        }
