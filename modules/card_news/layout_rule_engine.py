import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class LayoutRuleEngine:
    """
    layout_type별 시각 규칙(title_style, body_style, image_ratio, cta_position,
    highlight_color, background_tone)을 제공한다.

    지원 Layout: notebook, dark_editorial, bold_ai, character_diary, comparison,
    tutorial, checklist, timeline, warning, number_list.

    규칙은 templates/card_news_layout_rules.json에서 읽으며, 파일이 없거나
    손상되어도 하드코딩된 기본 규칙으로 동작한다. 알 수 없는 layout_type이
    들어와도 예외를 던지지 않고 default_layout(bold_ai) 규칙으로 대체한다.
    """

    DEFAULT_LAYOUT = "bold_ai"

    FALLBACK_RULES: Dict[str, Dict[str, str]] = {
        "notebook": {
            "title_style": "handwritten_bold",
            "body_style": "ruled_notes",
            "image_ratio": "1:1",
            "cta_position": "bottom_center",
            "highlight_color": "#e63946",
            "background_tone": "light_paper",
        },
        "dark_editorial": {
            "title_style": "serif_white_bold",
            "body_style": "serif_light_gray",
            "image_ratio": "4:5",
            "cta_position": "bottom_right",
            "highlight_color": "#f4c95d",
            "background_tone": "dark",
        },
        "bold_ai": {
            "title_style": "sans_black_bold",
            "body_style": "sans_white_medium",
            "image_ratio": "1:1",
            "cta_position": "bottom_center",
            "highlight_color": "#ffd60a",
            "background_tone": "dark_gradient",
        },
        "character_diary": {
            "title_style": "rounded_soft",
            "body_style": "rounded_casual",
            "image_ratio": "1:1",
            "cta_position": "bottom_left",
            "highlight_color": "#ff8fa3",
            "background_tone": "pastel",
        },
        "comparison": {
            "title_style": "split_header",
            "body_style": "two_column",
            "image_ratio": "1:1",
            "cta_position": "bottom_center",
            "highlight_color": "#457b9d",
            "background_tone": "split_light_dark",
        },
        "tutorial": {
            "title_style": "numbered_step_bold",
            "body_style": "step_by_step",
            "image_ratio": "1:1",
            "cta_position": "bottom_center",
            "highlight_color": "#2a9d8f",
            "background_tone": "light_clean",
        },
        "checklist": {
            "title_style": "checkbox_bold",
            "body_style": "checklist_items",
            "image_ratio": "1:1",
            "cta_position": "bottom_center",
            "highlight_color": "#06d6a0",
            "background_tone": "light_clean",
        },
        "timeline": {
            "title_style": "sequential_bold",
            "body_style": "timeline_marker",
            "image_ratio": "1:1",
            "cta_position": "bottom_right",
            "highlight_color": "#f77f00",
            "background_tone": "light_gradient",
        },
        "warning": {
            "title_style": "alert_bold",
            "body_style": "warning_box",
            "image_ratio": "1:1",
            "cta_position": "bottom_center",
            "highlight_color": "#d62828",
            "background_tone": "warning_light",
        },
        "number_list": {
            "title_style": "big_number_bold",
            "body_style": "ranked_list",
            "image_ratio": "1:1",
            "cta_position": "bottom_center",
            "highlight_color": "#3a86ff",
            "background_tone": "light_clean",
        },
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.template = self._load_template()
        self.rules = self.template.get("layouts") or self.FALLBACK_RULES
        self.default_layout = self.template.get("default_layout", self.DEFAULT_LAYOUT)

    def get_rule(self, layout_type: str) -> Dict[str, Any]:
        try:
            return self._get_rule(str(layout_type or ""))
        except Exception:
            fallback_rule = dict(self.FALLBACK_RULES[self.DEFAULT_LAYOUT])
            fallback_rule["layout_type"] = self.DEFAULT_LAYOUT
            fallback_rule["fallback_used"] = True
            return fallback_rule

    def _get_rule(self, layout_type: str) -> Dict[str, Any]:
        rule = self.rules.get(layout_type)

        if not isinstance(rule, dict):
            rule = self.rules.get(self.default_layout) or self.FALLBACK_RULES[self.DEFAULT_LAYOUT]
            resolved = dict(rule)
            resolved["layout_type"] = self.default_layout
            resolved["fallback_used"] = True
            return resolved

        resolved = dict(rule)
        resolved["layout_type"] = layout_type
        resolved["fallback_used"] = False
        return resolved

    def supported_layouts(self) -> List[str]:
        try:
            return list(self.rules.keys())
        except Exception:
            return list(self.FALLBACK_RULES.keys())

    def _load_template(self) -> Dict[str, Any]:
        template_path = Path("templates/card_news_layout_rules.json")

        if not template_path.exists():
            return {"default_layout": self.DEFAULT_LAYOUT, "layouts": self.FALLBACK_RULES}

        try:
            with open(template_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict) and isinstance(data.get("layouts"), dict):
                return data
        except Exception:
            pass

        return {"default_layout": self.DEFAULT_LAYOUT, "layouts": self.FALLBACK_RULES}
