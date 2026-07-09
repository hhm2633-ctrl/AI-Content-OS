from typing import Any, Dict


class CTASelector:
    """
    pattern_type을 기준으로 cta_type을 선택한다.
    benchmark/CTA_LIBRARY.md / CONTENT_PATTERNS.md 값 체계를 따른다.
    """

    CTA_TYPES = [
        "save",
        "comment",
        "dm",
        "profile",
        "follow",
    ]

    PATTERN_CTA_MAP = {
        "number_list": "save",
        "warning": "save",
        "comparison": "comment",
        "tutorial": "follow",
        "story": "comment",
        "resource": "save",
        "funnel": "dm",
    }

    def __init__(self, config=None):
        self.config = config or {}

    def select(self, category: str, pattern_type: str) -> Dict[str, Any]:
        cta_type = self.PATTERN_CTA_MAP.get(str(pattern_type), "save")
        reason = f"pattern_type '{pattern_type}' 기준으로 '{cta_type}' CTA를 선택함."

        return {"cta_type": cta_type, "reason": reason}
