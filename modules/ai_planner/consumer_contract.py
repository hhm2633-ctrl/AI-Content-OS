from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

# planner_confidence가 이 값 이상이어야 Hint를 적용 후보로 고려한다.
#
# 근거: PlannerDecisionEngine(Sprint 15-1)의 실제 관측값 기준 - 실제 topic
# 신호가 있지만 카테고리 키워드가 전혀 매칭되지 않아 기본 카테고리('트렌드')로
# 분류된 경우 confidence_score는 약 0.35 수준(quality_score 기반 base=0.5에서
# keyword_weights 없음(-0.1), 기본 카테고리(-0.05) 감점)이고, 실제로 카테고리가
# 분류되고 quality_score가 준수한 경우는 0.6~0.9대로 관측된다. 0.5는 "키워드가
# 전혀 안 잡혀 기본값으로 대체된" 상태와 "실제로 분류된" 상태를 가르는 현실적인
# 경계값이다.
MIN_CONFIDENCE_FOR_HINT_APPLICATION = 0.5


class PlannerConsumerContract(object):
    """
    AI Planner Consumer Contract (Sprint 15-2).

    CTO 핵심 결정: Planner 결과는 **강제 명령이 아니라 검증된 힌트**다. 기존
    Engine의 정상 선택 로직과 fallback은 절대 제거하지 않는다. 이 클래스는 그
    "검증" 자체를 담당하는 공용 규칙이며, 실제로 무엇을 어떻게 바꿀지는 다루지
    않는다(그건 `planner_consumer_adapter.py::PlannerConsumerAdapter`의 몫이다).

    소비 우선순위(4개 조건 모두 충족해야 Hint 적용):

    1. Planner 결과 유효 (`is_result_valid`): `schema_valid=True` 그리고
       `status="planner_decided"` - Sprint 15-1에서 실제 topic 신호가 없을 때
       반환되는 `status="planner_not_decided"`는 애초에 Hint 후보가 아니다.
    2. `planner_confidence`가 기준(`MIN_CONFIDENCE_FOR_HINT_APPLICATION`) 이상
       (`meets_confidence_threshold`).
    3. Consumer Engine이 그 값을 실제로 지원함 (`is_value_supported`) - Planner가
       만들어낸 값이 아니라, Consumer Engine 자신의 실제 enum에 속하는 값이어야
       한다(예: `PatternSelector.PATTERN_TYPES`).
    4. 기존 Engine의 안전 규칙과 충돌하지 않음 (`safety_conflict=False`) - 예:
       PatternEngineModule 자신의 `confidence_score < LOW_CONFIDENCE_THRESHOLD`
       강제 안전 전환, TopicClassifier의 blocked 카테고리 감지. 이 값은 이
       클래스가 계산하지 않는다 - 호출자(Adapter)가 실제 Engine의 안전 신호를
       그대로 전달한다.

    네 조건 중 하나라도 실패하면 Hint를 적용하지 않는다 - "그 외 -> 기존 Engine
    로직 유지"가 기본값이다. 모든 메서드는 어떤 입력에도 예외를 던지지 않는다.
    """

    MIN_CONFIDENCE_FOR_HINT_APPLICATION = MIN_CONFIDENCE_FOR_HINT_APPLICATION

    @classmethod
    def is_result_valid(cls, planner_result: Optional[Dict[str, Any]]) -> bool:
        try:
            if not isinstance(planner_result, dict):
                return False
            return bool(planner_result.get("schema_valid")) and planner_result.get("status") == "planner_decided"
        except Exception:
            return False

    @classmethod
    def meets_confidence_threshold(
        cls,
        planner_result: Optional[Dict[str, Any]],
        threshold: float = MIN_CONFIDENCE_FOR_HINT_APPLICATION,
    ) -> bool:
        try:
            if not isinstance(planner_result, dict):
                return False
            confidence = float(planner_result.get("planner_confidence", 0.0) or 0.0)
            return confidence >= float(threshold)
        except (TypeError, ValueError):
            return False

    @classmethod
    def is_value_supported(cls, value: Any, supported_values: Iterable[str]) -> bool:
        try:
            if not isinstance(value, str) or not value:
                return False
            return value in set(supported_values or [])
        except Exception:
            return False

    @classmethod
    def should_apply_hint(
        cls,
        planner_result: Optional[Dict[str, Any]],
        field: str,
        supported_values: Iterable[str],
        safety_conflict: bool,
        threshold: float = MIN_CONFIDENCE_FOR_HINT_APPLICATION,
    ) -> Tuple[bool, str]:
        """
        단일 값(scalar) Output 필드(`selected_pattern`/`selected_hook_strategy`/
        `selected_cta_strategy`/`selected_image_strategy`)에 대한 판정. 절대
        예외를 던지지 않는다 - 판정에 필요한 값이 무엇이든 이상해도 그냥
        "적용하지 않음"으로 안전하게 처리한다.
        """
        try:
            if not cls.is_result_valid(planner_result):
                return False, "planner_result가 유효하지 않음(schema_valid=False 또는 status != 'planner_decided')."

            if not cls.meets_confidence_threshold(planner_result, threshold):
                confidence = planner_result.get("planner_confidence") if isinstance(planner_result, dict) else None
                return False, f"planner_confidence({confidence})가 기준({threshold}) 미달."

            value = planner_result.get(field) if isinstance(planner_result, dict) else None

            if not cls.is_value_supported(value, supported_values):
                return False, f"'{field}' 값 '{value}'이 Consumer Engine이 지원하는 값 집합에 없음."

            if safety_conflict:
                return False, "기존 Engine의 안전 규칙(blocked/low-confidence 등)과 충돌하여 Hint를 적용하지 않음."

            confidence = planner_result.get("planner_confidence")
            return True, f"Planner Hint 적용: '{field}'='{value}' (planner_confidence={confidence})."
        except Exception as error:
            return False, f"Hint 적용 여부 판정 실패로 안전하게 미적용 처리함: {error}"

    @classmethod
    def should_apply_list_hint(
        cls,
        planner_result: Optional[Dict[str, Any]],
        field: str,
        item_validator: Callable[[Any], bool],
        threshold: float = MIN_CONFIDENCE_FOR_HINT_APPLICATION,
    ) -> Tuple[bool, str, List[Any]]:
        """
        목록(list) Output 필드(`knowledge_priority`/`competitor_reference`)에
        대한 판정. 이 필드들은 기존 선택을 대체하는 게 아니라 우선순위/참고
        힌트이므로 "안전 규칙과의 충돌" 개념이 없다 - 유효성 + confidence +
        항목별 지원 여부만 확인한다. 절대 예외를 던지지 않는다.
        """
        try:
            if not cls.is_result_valid(planner_result):
                return False, "planner_result가 유효하지 않음(schema_valid=False 또는 status != 'planner_decided').", []

            if not cls.meets_confidence_threshold(planner_result, threshold):
                confidence = planner_result.get("planner_confidence") if isinstance(planner_result, dict) else None
                return False, f"planner_confidence({confidence})가 기준({threshold}) 미달.", []

            values = planner_result.get(field) if isinstance(planner_result, dict) else None

            if not isinstance(values, list) or not values:
                return False, f"'{field}'가 비어 있어 적용할 Hint가 없음.", []

            valid_items = [item for item in values if cls._safe_validate(item_validator, item)]

            if not valid_items:
                return False, f"'{field}'의 모든 항목이 지원되지 않는 값이라 적용하지 않음.", []

            return True, f"Planner Hint 적용: '{field}'={valid_items}.", valid_items
        except Exception as error:
            return False, f"Hint 적용 여부 판정 실패로 안전하게 미적용 처리함: {error}", []

    @classmethod
    def _safe_validate(cls, item_validator: Callable[[Any], bool], item: Any) -> bool:
        try:
            return bool(item_validator(item))
        except Exception:
            return False

    @classmethod
    def describe(cls) -> Dict[str, Any]:
        """Codex/향후 Sprint가 소비 규칙을 코드로 그대로 확인할 수 있게 하는 요약."""
        return {
            "min_confidence_for_hint_application": cls.MIN_CONFIDENCE_FOR_HINT_APPLICATION,
            "consumption_gates": [
                "planner_result가 유효함 (schema_valid=True, status=planner_decided)",
                "planner_confidence가 기준 이상",
                "Consumer Engine이 그 값을 실제로 지원함",
                "기존 Engine의 안전 규칙과 충돌하지 않음",
            ],
            "on_any_gate_failure": "기존 Engine 로직/기본값을 그대로 유지한다 (Planner Hint는 절대 강제 명령이 아니다).",
        }
