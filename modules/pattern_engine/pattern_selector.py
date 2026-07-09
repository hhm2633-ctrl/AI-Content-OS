from typing import Any, Dict


class PatternSelector:
    """
    카테고리/confidence_score를 기준으로 콘텐츠 패턴 타입을 선택한다.
    benchmark/CONTENT_PATTERNS.md의 Engine Rule 값 체계를 따른다.
    """

    PATTERN_TYPES = [
        "number_list",
        "warning",
        "comparison",
        "tutorial",
        "story",
        "resource",
        "funnel",
    ]

    CATEGORY_PATTERN_MAP = {
        "AI": "tutorial",
        "부업": "warning",
        "경제": "number_list",
        "생활": "resource",
        "쇼핑": "comparison",
        "트렌드": "number_list",
    }

    LOW_CONFIDENCE_THRESHOLD = 0.3

    def __init__(self, config=None):
        self.config = config or {}

    def select(self, category: str, cluster: str, confidence_score: float) -> Dict[str, Any]:
        try:
            confidence_score = float(confidence_score or 0.0)
        except (TypeError, ValueError):
            confidence_score = 0.0

        pattern_type = self.CATEGORY_PATTERN_MAP.get(str(category), "resource")

        if confidence_score < self.LOW_CONFIDENCE_THRESHOLD:
            pattern_type = "resource"
            reason = (
                f"confidence_score({confidence_score})가 낮아 안전한 "
                "'resource' 패턴으로 대체함."
            )
        else:
            reason = f"category '{category}' 기준으로 '{pattern_type}' 패턴을 선택함."

        return {"pattern_type": pattern_type, "reason": reason}
