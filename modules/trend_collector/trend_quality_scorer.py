import re
from typing import Any, Dict, List, Set


class TrendQualityScorer:
    def __init__(self):
        self.source_scores = {
            "naver_news": 18,
            "nate_pann": 14,
            "google_trends": 16,
            "youtube": 13,
            "fmkorea": 10,
            "dcinside": 8,
            "bobaedream": 9,
            "ppomppu": 9,
            "manual": 6,
        }
        self.card_news_keywords = [
            "AI",
            "automation",
            "content",
            "creator",
            "Instagram",
            "side",
            "income",
            "workflow",
            "card",
            "news",
            "trend",
            "monetization",
        ]

    def score_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_titles: Set[str] = set()
        scored_items = []

        for item in items:
            scored_item = dict(item)
            quality_score = self.score_item(scored_item, seen_titles)
            scored_item["quality_score"] = quality_score
            scored_item["selection_reason"] = self.build_selection_reason(
                scored_item,
                seen_titles,
            )
            seen_titles.add(self._normalize_title(scored_item.get("keyword", "")))
            scored_items.append(scored_item)

        return scored_items

    def score_item(self, item: Dict[str, Any], seen_titles: Set[str]) -> int:
        score = 45
        title = str(item.get("keyword", "")).strip()
        normalized_title = self._normalize_title(title)

        score += self._title_length_score(title)
        score += self._keyword_match_score(title)
        score += self._source_score(item)
        score -= self._duplicate_penalty(normalized_title, seen_titles)
        score -= self._fallback_penalty(item)
        score -= self._sensitivity_penalty(title)

        return max(0, min(100, int(round(score))))

    def build_selection_reason(
        self,
        item: Dict[str, Any],
        seen_titles: Set[str],
    ) -> str:
        reasons = []
        title = str(item.get("keyword", "")).strip()
        normalized_title = self._normalize_title(title)
        source = str(item.get("source") or item.get("source_id") or "unknown")
        method = str(item.get("collection_method", ""))

        if self._title_length_score(title) >= 10:
            reasons.append("제목 길이가 카드뉴스 주제로 적절함")
        else:
            reasons.append("제목 길이 보정이 필요함")

        if self._keyword_match_score(title) > 0:
            reasons.append("콘텐츠화하기 좋은 키워드가 포함됨")

        if source in {"nate_pann", "fmkorea", "dcinside", "bobaedream", "ppomppu"}:
            reasons.append("국내 커뮤니티 반응형 주제로 판단됨")
        elif source == "naver_news":
            reasons.append("뉴스 기반 이슈로 확장 가능함")
        elif source == "google_trends":
            reasons.append("검색 관심도 기반 주제로 판단됨")

        duplicate_penalty = self._duplicate_penalty(normalized_title, seen_titles)
        if duplicate_penalty >= 20:
            reasons.append("중복 제목이라 점수 일부 감점")
        elif duplicate_penalty > 0:
            reasons.append("중복 가능성이 있어 점수 일부 감점")

        if item.get("is_fallback", False):
            if method.endswith("_cache"):
                reasons.append("캐시 기반이라 최신성은 낮지만 사용 가능")
            elif method == "settings_keyword_fallback":
                reasons.append("fallback 데이터라 신뢰도는 낮지만 기본 주제로 사용 가능")
            elif method == "placeholder_fallback":
                reasons.append("placeholder fallback이라 우선순위는 낮음")

        if self._sensitivity_penalty(title) > 0:
            reasons.append("민감한 표현 가능성이 있어 점수 감점")

        if not reasons:
            reasons.append("기본 품질 기준을 충족한 후보로 판단됨")

        return "; ".join(reasons[:4]) + "."

    def _title_length_score(self, title: str) -> int:
        length = len(title)

        if 12 <= length <= 55:
            return 18

        if 6 <= length < 12 or 55 < length <= 80:
            return 10

        if 1 <= length < 6 or 80 < length <= 120:
            return 2

        return -12

    def _keyword_match_score(self, title: str) -> int:
        title_lower = title.lower()
        matches = 0

        for keyword in self.card_news_keywords:
            if keyword.lower() in title_lower:
                matches += 1

        return min(18, matches * 6)

    def _source_score(self, item: Dict[str, Any]) -> int:
        source = str(item.get("source") or item.get("source_id") or "unknown")
        return self.source_scores.get(source, 5)

    def _duplicate_penalty(self, normalized_title: str, seen_titles: Set[str]) -> int:
        if not normalized_title:
            return 8

        if normalized_title in seen_titles:
            return 25

        for seen_title in seen_titles:
            if self._is_similar(normalized_title, seen_title):
                return 12

        return 0

    def _fallback_penalty(self, item: Dict[str, Any]) -> int:
        if not item.get("is_fallback", False):
            return 0

        method = str(item.get("collection_method", ""))

        if method.endswith("_cache"):
            return 8

        if method == "settings_keyword_fallback":
            return 18

        if method == "placeholder_fallback":
            return 28

        return 16

    def _sensitivity_penalty(self, title: str) -> int:
        sensitive_patterns = [
            "death",
            "crime",
            "suicide",
            "violence",
            "scandal",
            "adult",
            "hate",
        ]
        title_lower = title.lower()

        for pattern in sensitive_patterns:
            if pattern in title_lower:
                return 18

        return 0

    def _normalize_title(self, title: str) -> str:
        normalized = str(title).lower()
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = re.sub(r"[^0-9a-z가-힣 ]+", "", normalized)
        return normalized.strip()

    def _is_similar(self, title: str, other_title: str) -> bool:
        if not title or not other_title:
            return False

        if title in other_title or other_title in title:
            return True

        title_tokens = set(title.split())
        other_tokens = set(other_title.split())

        if not title_tokens or not other_tokens:
            return False

        overlap = len(title_tokens & other_tokens)
        smaller = min(len(title_tokens), len(other_tokens))

        return overlap / smaller >= 0.7
