from typing import Any, Dict


class HookSelector:
    """
    pattern_type을 기준으로 hook_type을 선택한다.
    benchmark/HOOK_LIBRARY.md / CONTENT_PATTERNS.md 값 체계를 따른다.
    """

    HOOK_TYPES = [
        "attention",
        "saveable_tip",
        "authority",
        "contrarian",
        "pain_point",
    ]

    PATTERN_HOOK_MAP = {
        "number_list": "saveable_tip",
        "warning": "attention",
        "comparison": "contrarian",
        "tutorial": "pain_point",
        "story": "authority",
        "resource": "saveable_tip",
        "funnel": "attention",
    }

    def __init__(self, config=None):
        self.config = config or {}

    def select(self, category: str, pattern_type: str) -> Dict[str, Any]:
        hook_type = self.PATTERN_HOOK_MAP.get(str(pattern_type), "saveable_tip")
        reason = f"pattern_type '{pattern_type}' 기준으로 '{hook_type}' 훅을 선택함."

        return {"hook_type": hook_type, "reason": reason}
