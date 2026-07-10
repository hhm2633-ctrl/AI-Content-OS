from typing import Any, Dict, List, Optional


class KnowledgeRanker(object):
    """
    Knowledge Engine - Ranker.

    score.overall_score 기준으로 Knowledge 항목을 정렬하고 rank를 부여한다.
    정렬 실패 시 원본 순서를 그대로 반환한다 (예외로 workflow를 깨지 않음).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def rank(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        try:
            sortable = [dict(item) for item in (items or [])]
            sortable.sort(key=self._overall_score, reverse=True)

            for index, item in enumerate(sortable):
                item["rank"] = index + 1

            return sortable
        except Exception as error:
            print(f"Knowledge Ranker Failed: {error}")
            return list(items or [])

    def top_by_type(
        self,
        items: List[Dict[str, Any]],
        knowledge_type: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        try:
            matched = [item for item in (items or []) if item.get("type") == knowledge_type]
            matched.sort(key=self._overall_score, reverse=True)
            return matched[:limit]
        except Exception as error:
            print(f"Knowledge Ranker top_by_type Failed: {error}")
            return []

    def _overall_score(self, item: Dict[str, Any]) -> float:
        score = item.get("score") or {}

        try:
            return float(score.get("overall_score", 0.0))
        except Exception:
            return 0.0
