from typing import Any, Dict, Optional


class PlanningContext(object):
    """
    AI Planner - Input Contract (Sprint 15-0A, Dependency Repair).

    Sprint 15-0 defined `PlanningContext` with 8 fields, but 5 of them
    (`pattern_result`, `knowledge_result`, `trend_memory_result`,
    `competitor_result`, `image_strategy_result`) do not exist yet at the
    Planner's actual `WorkflowEngine` execution position (after
    `TopicEngineModule`, before `PatternEngineModule`) - those stages run
    *later*. Sprint 15-0A corrects this by splitting inputs into two kinds
    (see `PlannerContract.RUNTIME_INPUT_FIELDS` / `HISTORICAL_INPUT_FIELDS`,
    which this class's fields must exactly match):

    - **Runtime Inputs** (exist for real at this point in the current run):
      `trend_result` and `topic_result` are the previous `WorkflowEngine`
      stages' actual results. `brand_profile` is different in kind - it is not
      a prior stage's output but static configuration
      (`config/brand_profile.json`, loaded via
      `modules/brand_dna_engine/brand_profile_loader.py::BrandProfileLoader`,
      the same loader Brand DNA Engine already uses - see
      `planner_interface.py::PlannerInterface.load_brand_profile()`). It is
      grouped with Runtime Inputs because it is available unconditionally at
      the Planner's position (not accumulated *past-run* data), not because it
      is produced by a prior `WorkflowEngine` stage.
    - **Historical Inputs** (accumulated data read from local storage, never
      this run's not-yet-produced results): `knowledge_history`,
      `trend_memory_history`, `competitor_history`, `brand_dna_history`,
      `performance_history`.

    This class does no I/O itself - it is a plain data container. Historical
    fields are populated by the caller, typically via
    `planner_interface.py::PlannerInterface.load_historical_inputs()`, which
    reads real accumulated data from each Engine's existing Interface/storage.
    All fields default to an empty dict when missing, so this class never
    raises regardless of what is passed in.
    """

    def __init__(
        self,
        trend_result: Optional[Dict[str, Any]] = None,
        topic_result: Optional[Dict[str, Any]] = None,
        brand_profile: Optional[Dict[str, Any]] = None,
        knowledge_history: Optional[Dict[str, Any]] = None,
        trend_memory_history: Optional[Dict[str, Any]] = None,
        competitor_history: Optional[Dict[str, Any]] = None,
        brand_dna_history: Optional[Dict[str, Any]] = None,
        performance_history: Optional[Dict[str, Any]] = None,
    ):
        # Runtime Inputs.
        self.trend_result = trend_result or {}
        self.topic_result = topic_result or {}
        self.brand_profile = brand_profile or {}

        # Historical Inputs.
        self.knowledge_history = knowledge_history or {}
        self.trend_memory_history = trend_memory_history or {}
        self.competitor_history = competitor_history or {}
        self.brand_dna_history = brand_dna_history or {}
        self.performance_history = performance_history or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trend_result": self.trend_result,
            "topic_result": self.topic_result,
            "brand_profile": self.brand_profile,
            "knowledge_history": self.knowledge_history,
            "trend_memory_history": self.trend_memory_history,
            "competitor_history": self.competitor_history,
            "brand_dna_history": self.brand_dna_history,
            "performance_history": self.performance_history,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "PlanningContext":
        """
        Never raises regardless of `data`'s type - non-dict input (None, a
        list, a string, an int, ...) is treated the same as an empty dict.
        """
        data = data if isinstance(data, dict) else {}

        return cls(
            trend_result=data.get("trend_result"),
            topic_result=data.get("topic_result"),
            brand_profile=data.get("brand_profile"),
            knowledge_history=data.get("knowledge_history"),
            trend_memory_history=data.get("trend_memory_history"),
            competitor_history=data.get("competitor_history"),
            brand_dna_history=data.get("brand_dna_history"),
            performance_history=data.get("performance_history"),
        )
