from datetime import datetime
from typing import Any, Dict, List, Optional

PLANNER_VERSION = "0.1.0-contract-only"

# AI Planner - Output Contract (Sprint 15-0). PlannerContract.OUTPUT_FIELDS와 반드시 일치한다.
REQUIRED_FIELDS: List[str] = [
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


def build_undecided_result(reason: str) -> Dict[str, Any]:
    """
    Sprint 15-0(Architecture Only) 기준의 "아직 아무것도 판단하지 않은" 상태의
    planner_result.json 스키마를 만든다.

    모든 결정 필드는 명시적으로 비어 있거나(None/[]/0.0) "아직 결정되지 않음"을
    뜻한다 - 진짜 판단처럼 보이는 그럴듯한 기본값을 채우지 않는다. 이는
    Sprint 13에서 확립된 Offline-First 원칙("실제 신호가 없으면 정직하게 빈
    상태로 기록한다")과 동일한 기준을 AI Planner에도 그대로 적용한 것이다.
    """
    return {
        "status": "planner_not_decided",
        "selected_pattern": None,
        "selected_hook_strategy": None,
        "selected_cta_strategy": None,
        "selected_image_strategy": None,
        "knowledge_priority": [],
        "competitor_reference": [],
        "content_strategy": None,
        "planner_confidence": 0.0,
        "planner_reason": reason,
        "planner_version": PLANNER_VERSION,
        "created_at": datetime.now().isoformat(),
    }


def validate_schema(result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    result dict가 REQUIRED_FIELDS를 모두 갖췄는지만 확인한다 - 값의 옳고 그름은
    판단하지 않는다(Sprint 15-0에는 실제 Decision Engine이 없으므로 "옳은 값"이라는
    개념 자체가 아직 없다). 예외를 던지지 않고 항상 안전한 결과를 반환한다.
    """
    try:
        if not isinstance(result, dict):
            return {"valid": False, "missing_fields": list(REQUIRED_FIELDS)}

        missing = [field for field in REQUIRED_FIELDS if field not in result]
        return {"valid": not missing, "missing_fields": missing}
    except Exception as error:
        return {"valid": False, "missing_fields": list(REQUIRED_FIELDS), "error": str(error)}
