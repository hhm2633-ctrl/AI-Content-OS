import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set


class TopTopicPicker:
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("storage/trends")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.selected_topic_path = self.output_dir / "selected_topic.json"

    def pick(self, trends: List[Dict[str, Any]]) -> Dict[str, Any]:
        deduped_candidates = self._dedupe_candidates(trends)

        if not deduped_candidates:
            selected_topic = self._placeholder_selected_topic()
            self.save(selected_topic)
            return selected_topic

        ranked_candidates = sorted(
            deduped_candidates,
            key=lambda item: (
                self._effective_score(item),
                item.get("quality_score", 0),
                item.get("score", 0),
            ),
            reverse=True,
        )
        best = ranked_candidates[0]
        selected_topic = self._build_selected_topic(best)
        self.save(selected_topic)
        return selected_topic

    def save(self, selected_topic: Dict[str, Any]) -> None:
        with open(self.selected_topic_path, "w", encoding="utf-8") as file:
            json.dump(selected_topic, file, ensure_ascii=False, indent=2)

    def _dedupe_candidates(self, trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sorted_trends = sorted(
            trends or [],
            key=lambda item: (
                item.get("quality_score", 0),
                item.get("score", 0),
            ),
            reverse=True,
        )
        seen_titles: Set[str] = set()
        deduped = []

        for trend in sorted_trends:
            title = str(trend.get("keyword", "")).strip()
            normalized_title = self._normalize_title(title)

            if not normalized_title:
                continue

            if self._is_duplicate(normalized_title, seen_titles):
                continue

            seen_titles.add(normalized_title)
            deduped.append(trend)

        return deduped

    def _build_selected_topic(self, trend: Dict[str, Any]) -> Dict[str, Any]:
        quality_score = int(trend.get("quality_score", 0))
        is_fallback = bool(trend.get("is_fallback", False))
        collection_method = trend.get("collection_method", "unknown")

        return {
            "title": str(trend.get("keyword", "AI content automation")).strip(),
            "source": trend.get("source", "unknown"),
            "quality_score": quality_score,
            "selection_reason": trend.get("selection_reason", ""),
            "collection_method": collection_method,
            "picked_reason": self._build_picked_reason(
                quality_score=quality_score,
                is_fallback=is_fallback,
                collection_method=collection_method,
            ),
            "is_fallback": is_fallback,
            "picked_at": datetime.now().isoformat(),
        }

    def _placeholder_selected_topic(self) -> Dict[str, Any]:
        return {
            "title": "AI content automation",
            "source": "placeholder",
            "quality_score": 50,
            "selection_reason": "후보가 비어 있어 안전한 기본 주제로 선택됨.",
            "collection_method": "placeholder_fallback",
            "picked_reason": "수집 후보가 없어 workflow 유지를 위한 기본 주제를 선택함.",
            "is_fallback": True,
            "picked_at": datetime.now().isoformat(),
        }

    def _effective_score(self, item: Dict[str, Any]) -> int:
        score = int(item.get("quality_score", 0))

        if item.get("is_fallback", False):
            method = str(item.get("collection_method", ""))

            if method.endswith("_cache"):
                score -= 4
            elif method == "settings_keyword_fallback":
                score -= 8
            elif method == "placeholder_fallback":
                score -= 12
            else:
                score -= 6

        return max(0, score)

    def _build_picked_reason(
        self,
        quality_score: int,
        is_fallback: bool,
        collection_method: str,
    ) -> str:
        if is_fallback:
            if collection_method.endswith("_cache"):
                return "quality_score가 높고 캐시 기반 fallback 중 가장 적합해 선택함."

            return "실시간 수집 실패 상황에서 quality_score가 높은 fallback 후보로 선택함."

        return "quality_score가 높고 중복 제거 후 카드뉴스 주제로 가장 적합해 선택함."

    def _normalize_title(self, title: str) -> str:
        normalized = str(title).lower()
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = re.sub(r"[^0-9a-z가-힣 ]+", "", normalized)
        return normalized.strip()

    def _is_duplicate(self, normalized_title: str, seen_titles: Set[str]) -> bool:
        if normalized_title in seen_titles:
            return True

        title_tokens = set(normalized_title.split())

        for seen_title in seen_titles:
            if normalized_title in seen_title or seen_title in normalized_title:
                return True

            seen_tokens = set(seen_title.split())

            if not title_tokens or not seen_tokens:
                continue

            overlap = len(title_tokens & seen_tokens)
            smaller = min(len(title_tokens), len(seen_tokens))

            if smaller and overlap / smaller >= 0.7:
                return True

        return False
