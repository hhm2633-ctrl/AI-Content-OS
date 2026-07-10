from typing import Any, Dict, Optional


class PlanningContext(object):
    """
    AI Planner - Input Contract (Sprint 15-0, Architecture Only).

    AI Planner가 앞으로 판단을 내릴 때 참고할 8가지 입력을 하나의 구조로
    정의한다 (PlannerContract.INPUT_FIELDS와 반드시 일치). Sprint 15-0에서는
    이 Contract만 확정하며, 이 값들을 실제로 읽어 판단하는 로직은 구현하지
    않는다 - PlannerModule은 Skeleton이다.

    각 입력은 이미 WorkflowEngine 파이프라인의 다른 Engine이 실제로 만들어내는
    결과를 그대로 참조하도록 설계되었다 - 이 클래스가 새로운 수집/생성 로직을
    추가하지 않는다. 모든 필드는 dict이며, 누락 시 빈 dict로 안전하게 채워진다.
    """

    def __init__(
        self,
        trend_result: Optional[Dict[str, Any]] = None,
        topic_result: Optional[Dict[str, Any]] = None,
        pattern_result: Optional[Dict[str, Any]] = None,
        knowledge_result: Optional[Dict[str, Any]] = None,
        trend_memory_result: Optional[Dict[str, Any]] = None,
        competitor_result: Optional[Dict[str, Any]] = None,
        brand_profile: Optional[Dict[str, Any]] = None,
        image_strategy_result: Optional[Dict[str, Any]] = None,
    ):
        self.trend_result = trend_result or {}
        self.topic_result = topic_result or {}
        self.pattern_result = pattern_result or {}
        self.knowledge_result = knowledge_result or {}
        self.trend_memory_result = trend_memory_result or {}
        self.competitor_result = competitor_result or {}
        self.brand_profile = brand_profile or {}
        self.image_strategy_result = image_strategy_result or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trend_result": self.trend_result,
            "topic_result": self.topic_result,
            "pattern_result": self.pattern_result,
            "knowledge_result": self.knowledge_result,
            "trend_memory_result": self.trend_memory_result,
            "competitor_result": self.competitor_result,
            "brand_profile": self.brand_profile,
            "image_strategy_result": self.image_strategy_result,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "PlanningContext":
        data = data if isinstance(data, dict) else {}

        return cls(
            trend_result=data.get("trend_result"),
            topic_result=data.get("topic_result"),
            pattern_result=data.get("pattern_result"),
            knowledge_result=data.get("knowledge_result"),
            trend_memory_result=data.get("trend_memory_result"),
            competitor_result=data.get("competitor_result"),
            brand_profile=data.get("brand_profile"),
            image_strategy_result=data.get("image_strategy_result"),
        )
