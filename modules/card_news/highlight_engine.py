import re
from typing import Any, Dict, List, Optional, Set


class HighlightEngine:
    """
    슬라이드 headline/body 텍스트에서 강조할 요소(중요 단어, 숫자, 경고, 비교,
    CTA, 주제 키워드)를 추출한다. 정규식/키워드 매칭 기반이며 외부 NLP 의존성이
    없다. 계산에 실패해도 예외를 던지지 않고 빈 결과를 반환한다.
    """

    NUMBER_PATTERN = re.compile(r"\d+[%가-힣]*")

    WARNING_WORDS = ["주의", "위험", "실수", "손해", "절대", "금지"]
    COMPARISON_WORDS = ["보다", "대신", "vs", "비교", "차이"]
    CTA_WORDS = ["저장", "팔로우", "댓글", "공유", "DM", "프로필"]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def highlight(
        self,
        content_result: Optional[Dict[str, Any]],
        topic_intelligence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            return self._highlight(content_result or {}, topic_intelligence or {})
        except Exception:
            return {
                "highlight_keywords": [],
                "slide_highlights": [],
                "reason": "강조 요소 계산 실패로 빈 값을 반환함.",
            }

    def _highlight(
        self,
        content_result: Dict[str, Any],
        topic_intelligence: Dict[str, Any],
    ) -> Dict[str, Any]:
        slides = content_result.get("slides", [])
        if not isinstance(slides, list):
            slides = []

        topic_keywords: Set[str] = set()
        raw_keywords = topic_intelligence.get("keywords", [])
        if isinstance(raw_keywords, list):
            topic_keywords = {str(keyword) for keyword in raw_keywords if keyword}

        slide_highlights = []
        all_keywords: Set[str] = set()

        for slide in slides:
            if not isinstance(slide, dict):
                continue

            text = f"{slide.get('headline', '')} {slide.get('body', '')}"
            found = self._extract_highlights(text, topic_keywords)

            slide_highlights.append(
                {
                    "page": slide.get("page"),
                    "role": slide.get("role"),
                    "highlights": found,
                }
            )
            all_keywords.update(item["text"] for item in found)

        return {
            "highlight_keywords": sorted(all_keywords),
            "slide_highlights": slide_highlights,
            "reason": f"{len(slide_highlights)}개 슬라이드에서 강조 요소 {len(all_keywords)}건 추출함.",
        }

    def _extract_highlights(self, text: str, topic_keywords: Set[str]) -> List[Dict[str, str]]:
        found: List[Dict[str, str]] = []

        for match in self.NUMBER_PATTERN.finditer(text):
            found.append({"type": "number", "text": match.group()})

        for word in self.WARNING_WORDS:
            if word in text:
                found.append({"type": "warning", "text": word})

        for word in self.COMPARISON_WORDS:
            if word in text:
                found.append({"type": "comparison", "text": word})

        for word in self.CTA_WORDS:
            if word in text:
                found.append({"type": "cta", "text": word})

        for keyword in topic_keywords:
            if keyword and keyword in text:
                found.append({"type": "topic_keyword", "text": keyword})

        return found
