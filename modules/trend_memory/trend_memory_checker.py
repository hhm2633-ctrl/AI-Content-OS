from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional


class TrendMemoryChecker(object):
    """
    Trend Memory - 중복 방지 검사.

    최근 기록(topic/hook_type/cta_type/layout_type/image_source)과 이번 실행을
    비교해 topic_repeat_risk와 각 요소별 반복 횟수를 계산한다. 생성 자체를 막지는
    않고(파이프라인 흐름 변경 금지), 위험 신호만 기록한다.
    """

    HIGH_SIMILARITY_THRESHOLD = 0.85
    RECENT_WINDOW = 10

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def check(self, current: Dict[str, Any], recent_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            return self._check(current or {}, recent_records or [])
        except Exception as error:
            return {
                "topic_repeat_risk": "low",
                "topic_similarity": 0.0,
                "matched_topic": "",
                "element_repeat_counts": {},
                "reason": f"trend_memory 중복 검사 실패로 안전하게 low 처리함: {error}",
            }

    def _check(self, current: Dict[str, Any], recent_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        window = recent_records[-self.RECENT_WINDOW:]

        current_topic = str(current.get("topic_title", ""))
        best_similarity = 0.0
        best_match = ""

        for record in window:
            similarity = self._similarity(current_topic, str(record.get("topic_title", "")))

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = str(record.get("topic_title", ""))

        if best_similarity >= self.HIGH_SIMILARITY_THRESHOLD:
            topic_repeat_risk = "high"
        elif best_similarity >= 0.5:
            topic_repeat_risk = "medium"
        else:
            topic_repeat_risk = "low"

        element_repeat_counts = {}
        for field in ("hook_type", "cta_type", "layout_type", "image_source"):
            value = str(current.get(field, ""))
            if not value:
                continue

            element_repeat_counts[field] = sum(
                1 for record in window if str(record.get(field, "")) == value
            )

        return {
            "topic_repeat_risk": topic_repeat_risk,
            "topic_similarity": round(best_similarity, 4),
            "matched_topic": best_match,
            "element_repeat_counts": element_repeat_counts,
            "reason": f"최근 {len(window)}건과 비교해 topic 유사도 {round(best_similarity, 4)}로 '{topic_repeat_risk}' 판정.",
        }

    def _similarity(self, text_a: str, text_b: str) -> float:
        text_a = str(text_a or "").strip().lower()
        text_b = str(text_b or "").strip().lower()

        if not text_a or not text_b:
            return 0.0

        return SequenceMatcher(None, text_a, text_b).ratio()
