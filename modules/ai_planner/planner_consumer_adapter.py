from typing import Any, Dict, Optional

from modules.ai_planner.consumer_contract import PlannerConsumerContract
from modules.image_strategy.image_source_selector import ImageSourceSelector
from modules.knowledge_engine.knowledge_extractor import KnowledgeExtractor
from modules.pattern_engine.cta_selector import CTASelector
from modules.pattern_engine.hook_selector import HookSelector
from modules.pattern_engine.pattern_selector import PatternSelector


class PlannerConsumerAdapter(object):
    """
    AI Planner Consumer Adapter (Sprint 15-2).

    각 `resolve_*` 메서드는 두 개의 이미 계산된 후보값 - Planner의 힌트값과
    호출측 Engine이 자신의 기존 로직/fallback으로 이미 계산해 둔 기본값 - 중
    하나를 고른다. 이 클래스는 **판단 로직을 대체하지 않는다** - `PatternSelector`/
    `HookSelector`/`CTASelector`/`ImageSourceSelector`를 다시 실행하지 않고,
    호출자가 이미 실행한 결과를 그대로 인자로 받는다. 선택 기준은 전부
    `consumer_contract.py::PlannerConsumerContract`에 있다.

    Sprint 15-2에서는 어떤 실제 Engine도 이 Adapter를 호출하지 않았다("소비 규칙
    구현"만이 범위였다). Sprint 15-3에서 `PatternEngineModule`/`ContentModule`/
    `ImageStrategyModule`/`KnowledgeModule`이 실제로 이 Adapter를 호출하도록
    연결됐고, `WorkflowEngine`도 `AIPlannerModule`을 실제로 실행한다 - 자세한
    통합 지점은 각 모듈의 `run()`과 `src/workflow_engine.py`를 참고.

    모든 메서드는 예외를 던지지 않는다 - 어떤 이유로든 판정이 실패하면 항상
    Engine의 기존 기본값을 그대로 반환한다(Hint 미적용과 동일하게 취급).

    `resolve_knowledge_priority`/`resolve_competitor_reference`도 동일한 불변식을
    따른다(Codex 검수 지적 반영, Sprint 15-2 중 추가) - `engine_default`로 호출측
    Engine이 이미 갖고 있던 목록을 받아, Hint가 거부되면 빈 목록이 아니라 그
    `engine_default`를 그대로 반환한다. 아직 실제로 이 값을 갖는 Engine이 없으므로
    `engine_default`를 생략하면 빈 목록(둘 다 애초에 새로운 기능이라 "기존 값"이
    없는 것과 동일)으로 안전하게 처리된다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    # ---- Pattern Engine ----

    def resolve_pattern(
        self,
        planner_result: Optional[Dict[str, Any]],
        engine_pattern_type: str,
        topic_confidence_score: float,
        blocked: bool,
    ) -> Dict[str, Any]:
        try:
            safety_conflict = self._pattern_safety_conflict(topic_confidence_score, blocked)

            applied, reason = PlannerConsumerContract.should_apply_hint(
                planner_result=planner_result,
                field="selected_pattern",
                supported_values=PatternSelector.PATTERN_TYPES,
                safety_conflict=safety_conflict,
            )

            if applied:
                return self._applied_result("pattern_type", planner_result["selected_pattern"], reason)

            return self._default_result("pattern_type", engine_pattern_type, reason)
        except Exception as error:
            return self._default_result(
                "pattern_type", engine_pattern_type, f"Hint 판정 실패로 기존 값을 유지함: {error}"
            )

    # ---- Content Engine (hook/cta) ----

    def resolve_hook(
        self,
        planner_result: Optional[Dict[str, Any]],
        engine_hook_type: str,
        blocked: bool,
    ) -> Dict[str, Any]:
        try:
            applied, reason = PlannerConsumerContract.should_apply_hint(
                planner_result=planner_result,
                field="selected_hook_strategy",
                supported_values=HookSelector.HOOK_TYPES,
                safety_conflict=bool(blocked),
            )

            if applied:
                return self._applied_result("hook_type", planner_result["selected_hook_strategy"], reason)

            return self._default_result("hook_type", engine_hook_type, reason)
        except Exception as error:
            return self._default_result(
                "hook_type", engine_hook_type, f"Hint 판정 실패로 기존 값을 유지함: {error}"
            )

    def resolve_cta(
        self,
        planner_result: Optional[Dict[str, Any]],
        engine_cta_type: str,
        blocked: bool,
    ) -> Dict[str, Any]:
        try:
            applied, reason = PlannerConsumerContract.should_apply_hint(
                planner_result=planner_result,
                field="selected_cta_strategy",
                supported_values=CTASelector.CTA_TYPES,
                safety_conflict=bool(blocked),
            )

            if applied:
                return self._applied_result("cta_type", planner_result["selected_cta_strategy"], reason)

            return self._default_result("cta_type", engine_cta_type, reason)
        except Exception as error:
            return self._default_result(
                "cta_type", engine_cta_type, f"Hint 판정 실패로 기존 값을 유지함: {error}"
            )

    # ---- Image Strategy Engine ----

    def resolve_image_strategy(
        self,
        planner_result: Optional[Dict[str, Any]],
        engine_content_type: str,
    ) -> Dict[str, Any]:
        try:
            # content_type 분류 자체에는 pattern_engine 같은 별도의 "안전 강제 전환"
            # 규칙이 없다(ContentTypeClassifier 참고) - 알려진 안전 충돌 개념이
            # 없으므로 safety_conflict=False로 고정한다.
            applied, reason = PlannerConsumerContract.should_apply_hint(
                planner_result=planner_result,
                field="selected_image_strategy",
                supported_values=ImageSourceSelector.SOURCE_PRIORITY.keys(),
                safety_conflict=False,
            )

            if applied:
                return self._applied_result("content_type", planner_result["selected_image_strategy"], reason)

            return self._default_result("content_type", engine_content_type, reason)
        except Exception as error:
            return self._default_result(
                "content_type", engine_content_type, f"Hint 판정 실패로 기존 값을 유지함: {error}"
            )

    # ---- Knowledge Engine (우선순위/참고 힌트 - 대체가 아니라 부가 정보) ----

    def resolve_knowledge_priority(
        self,
        planner_result: Optional[Dict[str, Any]],
        engine_default: Optional[Any] = None,
    ) -> Dict[str, Any]:
        # engine_default: 호출측 Engine이 이미 갖고 있던 우선순위 목록(없으면 빈 목록).
        # Hint가 거부되면 이 값을 그대로 반환한다 - scalar resolve_* 메서드와 동일하게
        # "기존 값을 절대 지우지 않는다"는 불변식을 여기서도 지킨다.
        default_priority = list(engine_default) if isinstance(engine_default, list) else []

        try:
            applied, reason, valid_items = PlannerConsumerContract.should_apply_list_hint(
                planner_result=planner_result,
                field="knowledge_priority",
                item_validator=lambda item: isinstance(item, str) and item in KnowledgeExtractor.KNOWLEDGE_TYPES,
            )

            return {
                "knowledge_priority": valid_items if applied else default_priority,
                "hint_applied": applied,
                "source": "planner_hint" if applied else "engine_default",
                "reason": reason,
            }
        except Exception as error:
            return {
                "knowledge_priority": default_priority,
                "hint_applied": False,
                "source": "engine_default",
                "reason": f"Hint 판정 실패로 기존 값을 유지함: {error}",
            }

    def resolve_competitor_reference(
        self,
        planner_result: Optional[Dict[str, Any]],
        engine_default: Optional[Any] = None,
    ) -> Dict[str, Any]:
        # engine_default: 호출측 Engine이 이미 갖고 있던 참고 목록(없으면 빈 목록).
        default_reference = list(engine_default) if isinstance(engine_default, list) else []

        try:
            applied, reason, valid_items = PlannerConsumerContract.should_apply_list_hint(
                planner_result=planner_result,
                field="competitor_reference",
                item_validator=lambda item: isinstance(item, str) and bool(item.strip()),
            )

            return {
                "competitor_reference": valid_items if applied else default_reference,
                "hint_applied": applied,
                "source": "planner_hint" if applied else "engine_default",
                "reason": reason,
            }
        except Exception as error:
            return {
                "competitor_reference": default_reference,
                "hint_applied": False,
                "source": "engine_default",
                "reason": f"Hint 판정 실패로 기존 값을 유지함: {error}",
            }

    # ---- 내부 헬퍼 ----

    def _pattern_safety_conflict(self, topic_confidence_score: Any, blocked: Any) -> bool:
        try:
            confidence = float(topic_confidence_score or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0

        return bool(blocked) or confidence < PatternSelector.LOW_CONFIDENCE_THRESHOLD

    def _applied_result(self, value_key: str, value: Any, reason: str) -> Dict[str, Any]:
        return {
            value_key: value,
            "hint_applied": True,
            "source": "planner_hint",
            "reason": reason,
        }

    def _default_result(self, value_key: str, value: Any, reason: str) -> Dict[str, Any]:
        return {
            value_key: value,
            "hint_applied": False,
            "source": "engine_default",
            "reason": reason,
        }


def build_consumption_metadata(
    planner_result: Optional[Dict[str, Any]],
    hint_applied: bool,
    requested_value: Any,
    original_value: Any,
    final_value: Any,
    reason: str,
) -> Dict[str, Any]:
    """
    AI Planner Consumption Metadata (Sprint 15-3).

    각 Consumer Engine(Pattern/Content/Image Strategy/Knowledge)이 `planner_consumption`
    필드에 기록할 표준 형태를 한 곳에서 만든다 - 필드 이름/의미가 Engine마다
    제각각이 되는 것을 막기 위한 순수 포맷팅 헬퍼다(판단 로직 없음, 새 Engine
    아님). 예외를 던지지 않는다.

    - `planner_available`: 이번 실행에서 Planner가 실제로 판단을 냈는가
      (`status == "planner_decided"`) - Planner가 실패했거나(`None`) 아직
      결정하지 못한 경우(`planner_not_decided`) `False`.
    - `planner_mode`: "unavailable"(Planner 결과 없음) / "fallback"(Planner는
      있었지만 게이트를 통과 못해 미적용) / "preferred"(Hint 적용됨).
    - `fallback_used`: Hint가 적용되지 않아 기존 Engine 기본값을 그대로 썼는가
      (`not hint_applied`) - 다른 Engine들의 "계산 자체가 실패했다"는 의미의
      `fallback_used`와는 별개로, 여기서는 "Planner Hint 대신 기존 Engine 값을
      썼다"는 뜻이다.
    """
    try:
        planner_available = (
            isinstance(planner_result, dict) and planner_result.get("status") == "planner_decided"
        )

        planner_confidence = 0.0
        if isinstance(planner_result, dict):
            try:
                planner_confidence = float(planner_result.get("planner_confidence", 0.0) or 0.0)
            except (TypeError, ValueError):
                planner_confidence = 0.0

        if not planner_available:
            planner_mode = "unavailable"
        elif hint_applied:
            planner_mode = "preferred"
        else:
            planner_mode = "fallback"

        return {
            "planner_available": planner_available,
            "planner_applied": bool(hint_applied),
            "planner_mode": planner_mode,
            "planner_confidence": planner_confidence,
            "requested_value": requested_value,
            "original_value": original_value,
            "final_value": final_value,
            "reason": reason,
            "fallback_used": not bool(hint_applied),
        }
    except Exception as error:
        return {
            "planner_available": False,
            "planner_applied": False,
            "planner_mode": "unavailable",
            "planner_confidence": 0.0,
            "requested_value": requested_value,
            "original_value": original_value,
            "final_value": original_value,
            "reason": f"consumption metadata 생성 실패: {error}",
            "fallback_used": True,
        }
