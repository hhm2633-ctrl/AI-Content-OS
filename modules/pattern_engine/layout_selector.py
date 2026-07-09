from typing import Any, Dict


class LayoutSelector:
    """
    카테고리를 기준으로 layout_type을 선택한다.
    benchmark/CONTENT_PATTERNS.md의 Visual Layout Patterns 값 체계를 따른다.
    """

    LAYOUT_TYPES = [
        "notebook",
        "dark_editorial",
        "bold_ai",
        "character_diary",
        "talking_head",
    ]

    CATEGORY_LAYOUT_MAP = {
        "AI": "bold_ai",
        "부업": "dark_editorial",
        "경제": "notebook",
        "생활": "notebook",
        "쇼핑": "bold_ai",
        "트렌드": "dark_editorial",
    }

    def __init__(self, config=None):
        self.config = config or {}

    def select(self, category: str, pattern_type: str) -> Dict[str, Any]:
        layout_type = self.CATEGORY_LAYOUT_MAP.get(str(category), "bold_ai")
        reason = f"category '{category}' 기준으로 '{layout_type}' 레이아웃을 선택함."

        return {"layout_type": layout_type, "reason": reason}
