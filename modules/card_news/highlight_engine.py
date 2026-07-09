import re
from typing import Any, Dict, List, Optional, Set


class HighlightEngine:
    """
    Highlight Engine v2 (CardNews Layout Intelligence Sprint 2).

    슬라이드 headline/body 텍스트에서 강조할 요소(숫자, 퍼센트, 경고, 비교, CTA,
    주제 키워드)와 슬라이드별 핵심 문장(key_sentence)을 추출한다. 정규식/키워드
    매칭 기반이며 외부 NLP 의존성이 없다.

    Sprint 2 개선:
    - 숫자/퍼센트를 분리 인식한다 (NUMBER_PATTERN/PERCENT_PATTERN) — "퍼센트 강조".
    - 슬라이드별 강조 개수를 MAX_HIGHLIGHTS_PER_SLIDE(3)로 제한하고, 우선순위
      (percent > number > warning > comparison > cta > topic_keyword) 순으로
      상위 항목만 남긴다 — "Slide별 강조 개수 제한".
    - 슬라이드 본문에서 강조 요소가 가장 많이 포함된 문장을 key_sentence로
      선정한다 — "핵심 문장 자동 강조". 강조 요소가 없으면 첫 문장(또는
      headline)을 key_sentence로 사용한다.
    - highlight_score(0.0~1.0)를 추가한다: 강조 요소가 1개 이상 있는 슬라이드
      비율로 계산하는 "Highlight 적합도" 지표다.

    계산에 실패해도 예외를 던지지 않고 빈 결과를 반환한다.
    """

    NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?[가-힣]*")
    PERCENT_PATTERN = re.compile(r"\d+(?:\.\d+)?\s?(?:%|퍼센트)")

    SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?。!?])\s+|\n+")

    WARNING_WORDS = ["주의", "위험", "실수", "손해", "절대", "금지"]
    COMPARISON_WORDS = ["보다", "대신", "vs", "비교", "차이"]
    CTA_WORDS = ["저장", "팔로우", "댓글", "공유", "DM", "프로필"]

    MAX_HIGHLIGHTS_PER_SLIDE = 3
    TYPE_PRIORITY = {
        "percent": 0,
        "number": 1,
        "warning": 2,
        "comparison": 3,
        "cta": 4,
        "topic_keyword": 5,
    }

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
                "highlight_score": 0.0,
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
        slides_with_highlight = 0

        for slide in slides:
            if not isinstance(slide, dict):
                continue

            headline = str(slide.get("headline", ""))
            body = str(slide.get("body", ""))
            text = f"{headline} {body}"

            found = self._extract_highlights(text, topic_keywords)
            limited = self._limit_highlights(found)

            if limited:
                slides_with_highlight += 1

            key_sentence = self._extract_key_sentence(body or headline, limited)

            slide_highlights.append(
                {
                    "page": slide.get("page"),
                    "role": slide.get("role"),
                    "highlights": limited,
                    "key_sentence": key_sentence,
                }
            )
            all_keywords.update(item["text"] for item in limited)

        total_slides = len(slide_highlights)
        highlight_score = round(slides_with_highlight / total_slides, 4) if total_slides else 0.0

        return {
            "highlight_keywords": sorted(all_keywords),
            "slide_highlights": slide_highlights,
            "highlight_score": highlight_score,
            "reason": (
                f"{total_slides}개 슬라이드 중 {slides_with_highlight}개에서 강조 요소 "
                f"{len(all_keywords)}건 추출함(highlight_score={highlight_score})."
            ),
        }

    def _extract_highlights(self, text: str, topic_keywords: Set[str]) -> List[Dict[str, str]]:
        found: List[Dict[str, str]] = []
        percent_spans = set()

        for match in self.PERCENT_PATTERN.finditer(text):
            found.append({"type": "percent", "text": match.group().strip()})
            percent_spans.add(match.span())

        for match in self.NUMBER_PATTERN.finditer(text):
            # 이미 퍼센트로 잡힌 구간과 겹치면 중복 집계하지 않는다.
            if any(match.start() >= start and match.end() <= end for start, end in percent_spans):
                continue
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

    def _limit_highlights(self, found: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if not found:
            return []

        deduped: List[Dict[str, str]] = []
        seen_text = set()

        for item in found:
            text = item.get("text", "")
            if text in seen_text:
                continue
            seen_text.add(text)
            deduped.append(item)

        deduped.sort(key=lambda item: self.TYPE_PRIORITY.get(item.get("type", ""), 99))

        return deduped[: self.MAX_HIGHLIGHTS_PER_SLIDE]

    def _extract_key_sentence(self, text: str, highlights: List[Dict[str, str]]) -> str:
        text = text.strip()

        if not text:
            return ""

        sentences = [part.strip() for part in self.SENTENCE_SPLIT_PATTERN.split(text) if part and part.strip()]

        if not sentences:
            return text

        if not highlights:
            return sentences[0]

        highlight_texts = [item.get("text", "") for item in highlights]

        best_sentence = sentences[0]
        best_hits = -1

        for sentence in sentences:
            hits = sum(1 for highlight_text in highlight_texts if highlight_text and highlight_text in sentence)

            if hits > best_hits:
                best_hits = hits
                best_sentence = sentence

        return best_sentence
