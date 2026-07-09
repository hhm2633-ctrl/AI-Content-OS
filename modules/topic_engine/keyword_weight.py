import re
from typing import Any, Dict, List, Tuple


class KeywordWeightEngine:
    """
    selected_topic와 trends 후보에서 키워드 가중치를 계산한다.
    실패해도 예외를 던지지 않고 빈 결과를 반환한다.
    """

    def __init__(self, config=None):
        self.config = config or {}
        self.min_token_length = 2
        self.max_keywords = 10

    def extract_tokens(self, text: str) -> List[str]:
        if not text:
            return []

        normalized = str(text).lower()
        normalized = re.sub(r"[^0-9a-z가-힣 ]+", " ", normalized)

        tokens = [
            token.strip()
            for token in normalized.split(" ")
            if len(token.strip()) >= self.min_token_length
        ]

        return tokens

    def compute_weights(
        self,
        selected_topic: Dict[str, Any],
        trends: List[Dict[str, Any]],
    ) -> Tuple[List[str], Dict[str, float]]:
        try:
            return self._compute_weights(selected_topic or {}, trends or [])
        except Exception:
            return [], {}

    def _compute_weights(
        self,
        selected_topic: Dict[str, Any],
        trends: List[Dict[str, Any]],
    ) -> Tuple[List[str], Dict[str, float]]:
        title = str(selected_topic.get("title") or selected_topic.get("keyword") or "")
        title_tokens = self.extract_tokens(title)

        raw_weights: Dict[str, float] = {}

        for token in title_tokens:
            raw_weights[token] = raw_weights.get(token, 0.0) + 5.0

        for trend in trends:
            if not isinstance(trend, dict):
                continue

            trend_score = trend.get("quality_score", trend.get("score", 0))

            try:
                trend_score = float(trend_score or 0)
            except (TypeError, ValueError):
                trend_score = 0.0

            trend_tokens = self.extract_tokens(str(trend.get("keyword", "")))
            bump = 1.0 + (trend_score / 100.0)

            for token in trend_tokens:
                raw_weights[token] = raw_weights.get(token, 0.0) + bump

        if not raw_weights:
            return [], {}

        max_weight = max(raw_weights.values()) or 1.0

        normalized_weights = {
            token: round(weight / max_weight, 4)
            for token, weight in raw_weights.items()
        }

        ranked_keywords = sorted(
            normalized_weights.keys(),
            key=lambda token: normalized_weights[token],
            reverse=True,
        )[: self.max_keywords]

        return ranked_keywords, {token: normalized_weights[token] for token in ranked_keywords}
