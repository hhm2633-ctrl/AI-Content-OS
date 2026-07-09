from typing import Any, Dict, Optional, Tuple


class LayoutSelector:
    """
    Pattern(pattern_prompt_meta), Topic(topic_intelligence), Brand Profile,
    Content Intelligence를 종합해 카드뉴스에 가장 적합한 layout_type을 선택한다.

    지원 layout_type은 LayoutRuleEngine과 동일한 10종
    (notebook, dark_editorial, bold_ai, character_diary, comparison, tutorial,
    checklist, timeline, warning, number_list)이다.

    계산에 실패해도 예외를 던지지 않고 안전한 기본 레이아웃(bold_ai)을 반환한다.
    """

    PATTERN_TYPE_LAYOUT_MAP = {
        "warning": "warning",
        "tutorial": "tutorial",
        "comparison": "comparison",
        "number_list": "number_list",
        "story": "character_diary",
        "resource": "checklist",
    }

    CATEGORY_LAYOUT_MAP = {
        "AI": "bold_ai",
        "부업": "dark_editorial",
        "경제": "notebook",
        "생활": "notebook",
        "쇼핑": "bold_ai",
        "트렌드": "dark_editorial",
    }

    DEFAULT_LAYOUT = "bold_ai"
    SAFE_LAYOUT = "notebook"
    LOW_QUALITY_THRESHOLD = 0.4

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def select(
        self,
        pattern_meta: Optional[Dict[str, Any]] = None,
        topic_intelligence: Optional[Dict[str, Any]] = None,
        brand_profile: Optional[Dict[str, Any]] = None,
        content_intelligence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            return self._select(
                pattern_meta or {},
                topic_intelligence or {},
                brand_profile or {},
                content_intelligence or {},
            )
        except Exception:
            return {
                "layout_type": self.DEFAULT_LAYOUT,
                "reason": "레이아웃 선택 계산 실패로 기본 레이아웃을 사용함.",
                "source": "error_fallback",
                "fallback_used": True,
            }

    def _select(
        self,
        pattern_meta: Dict[str, Any],
        topic_intelligence: Dict[str, Any],
        brand_profile: Dict[str, Any],
        content_intelligence: Dict[str, Any],
    ) -> Dict[str, Any]:
        pattern_type = str(pattern_meta.get("pattern_type", ""))
        category = str(topic_intelligence.get("category", ""))

        if pattern_type in self.PATTERN_TYPE_LAYOUT_MAP:
            layout_type = self.PATTERN_TYPE_LAYOUT_MAP[pattern_type]
            source = "pattern_type"
            reason = f"pattern_type '{pattern_type}' 기준으로 '{layout_type}' 레이아웃을 선택함."
        elif category in self.CATEGORY_LAYOUT_MAP:
            layout_type = self.CATEGORY_LAYOUT_MAP[category]
            source = "category"
            reason = f"category '{category}' 기준으로 '{layout_type}' 레이아웃을 선택함."
        else:
            layout_type, reason = self._brand_default(brand_profile)
            source = "brand_profile_default"

        risk_reason = self._risk_reason(content_intelligence)

        if risk_reason:
            layout_type = self.SAFE_LAYOUT
            source = "safety_override"
            reason = f"{risk_reason} 안전한 '{self.SAFE_LAYOUT}' 레이아웃으로 대체함."

        return {
            "layout_type": layout_type,
            "reason": reason,
            "source": source,
            "fallback_used": source in ("brand_profile_default", "safety_override", "error_fallback"),
        }

    def _brand_default(self, brand_profile: Dict[str, Any]) -> Tuple[str, str]:
        voice = str(brand_profile.get("voice", ""))

        if any(word in voice for word in ("친근", "편안", "다정")):
            layout_type = "character_diary"
        else:
            layout_type = self.DEFAULT_LAYOUT

        reason = (
            "pattern_type/category 정보가 없어 brand_profile voice "
            f"('{voice}') 기준으로 '{layout_type}' 레이아웃을 사용함."
        )

        return layout_type, reason

    def _risk_reason(self, content_intelligence: Dict[str, Any]) -> str:
        quality_score = content_intelligence.get("quality_score")

        if isinstance(quality_score, (int, float)) and quality_score < self.LOW_QUALITY_THRESHOLD:
            return f"quality_score({quality_score})가 낮아"

        if content_intelligence.get("brand_rule_passed") is False:
            return "브랜드 규칙 위반이 감지되어"

        if content_intelligence.get("duplicate_risk") == "high":
            return "중복 위험이 높아"

        return ""
