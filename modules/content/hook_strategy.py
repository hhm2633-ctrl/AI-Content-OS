from typing import Any, Dict, Optional


class HookStrategy:
    """
    Hook Library(benchmark/HOOK_LIBRARY.md) 기반으로 pattern_type/topic_intelligence에
    가장 적합한 hook_type을 선택한다. Pattern Engine의 hook_type(5종: attention,
    saveable_tip, authority, contrarian, pain_point)보다 넓은 7종 팔레트를 사용해
    Content Engine 단계에서 한 번 더 다듬는다. 실패해도 예외를 던지지 않고 안전한
    기본값을 반환한다.
    """

    HOOK_TYPES = [
        "attention",
        "saveable_tip",
        "authority",
        "contrarian",
        "pain_point",
        "beginner",
        "result_proof",
    ]

    # pattern_type 기준 Content Engine 전용 세분화 매핑.
    # tutorial/story는 Pattern Engine에 없는 beginner/result_proof로 세분화한다.
    PATTERN_HOOK_MAP = {
        "warning": "attention",
        "tutorial": "beginner",
        "comparison": "contrarian",
        "story": "result_proof",
        "number_list": "saveable_tip",
        "resource": "saveable_tip",
    }

    DEFAULT_HOOK_TYPE = "pain_point"

    def __init__(self, config=None):
        self.config = config or {}

    def select(
        self,
        pattern_plan: Optional[Dict[str, Any]],
        topic_intelligence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            return self._select(pattern_plan or {}, topic_intelligence or {})
        except Exception:
            return {
                "hook_type": self.DEFAULT_HOOK_TYPE,
                "reason": "Hook 선택 계산 실패로 기본 훅으로 대체함.",
            }

    def _select(
        self,
        pattern_plan: Dict[str, Any],
        topic_intelligence: Dict[str, Any],
    ) -> Dict[str, Any]:
        pattern_type = str(pattern_plan.get("pattern_type", ""))
        upstream_hook = str(pattern_plan.get("hook_type", ""))

        if pattern_type in self.PATTERN_HOOK_MAP:
            hook_type = self.PATTERN_HOOK_MAP[pattern_type]
            reason = (
                f"pattern_type '{pattern_type}' 콘텐츠 목적에 맞춰 Content Engine이 "
                f"'{hook_type}' 훅으로 세분화함."
            )
        elif upstream_hook in self.HOOK_TYPES:
            hook_type = upstream_hook
            reason = f"Content Engine 매핑에 없어 Pattern Engine의 '{hook_type}' 훅을 사용함."
        else:
            hook_type = self.DEFAULT_HOOK_TYPE
            reason = "pattern_type/hook_type 정보가 부족해 기본 훅으로 대체함."

        return {"hook_type": hook_type, "reason": reason}
