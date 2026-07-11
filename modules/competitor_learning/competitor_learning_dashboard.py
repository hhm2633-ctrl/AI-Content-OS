from datetime import datetime
from typing import Any, Dict, List, Optional


class CompetitorLearningDashboard:
    """
    Competitor Learning Engine - Dashboard (Sprint 18).

    Builds the storage/dashboard/daily_learning_report.json structure from
    this run's statistics + Knowledge Database summary. Pure computation, no
    I/O (CompetitorLearningStorage.save_dashboard persists the result).
    """

    def build(self, statistics: Dict[str, Any], knowledge_database: Dict[str, Any]) -> Dict[str, Any]:
        statistics = statistics if isinstance(statistics, dict) else {}
        knowledge_database = knowledge_database if isinstance(knowledge_database, dict) else {}

        competitor_statistics = statistics.get("competitor_statistics") or {}
        caption_summary = statistics.get("caption_summary") or {}

        return {
            "generated_at": datetime.now().isoformat(),
            "analyzed_account_count": competitor_statistics.get("account_count", 0),
            "analyzed_post_count": statistics.get("sample_size", 0),
            "hook_top10": self._top_n((statistics.get("hook_statistics") or {}).get("top", []), 10),
            "cta_top10": self._top_n((statistics.get("cta_statistics") or {}).get("top", []), 10),
            "pattern_top10": self._top_n((statistics.get("pattern_statistics") or {}).get("top", []), 10),
            "layout_top10": self._top_n((statistics.get("layout_statistics") or {}).get("top_layouts", []), 10),
            "avg_likes": self._weighted_avg(competitor_statistics, "avg_likes"),
            "avg_comments": self._weighted_avg(competitor_statistics, "avg_comments"),
            "new_learning_count": knowledge_database.get("new_count", 0),
            "caption_summary": caption_summary,
            "fallback_used": not statistics.get("sample_size"),
        }

    def _top_n(self, items: Any, n: int) -> List[Any]:
        return list(items or [])[:n]

    def _weighted_avg(self, competitor_statistics: Dict[str, Any], field: str) -> Optional[float]:
        """
        실제 관찰된 like/comment 수만 대상으로, 계정별 평균을 게시물 수로
        가중 평균한다. 관찰이 하나도 없으면 None (0으로 꾸며내지 않는다 -
        Offline-First 원칙).
        """
        accounts = competitor_statistics.get("accounts") or {}
        if not isinstance(accounts, dict):
            return None

        total_weighted = 0.0
        total_posts = 0

        for account in accounts.values():
            if not isinstance(account, dict):
                continue

            value = account.get(field)
            post_count = account.get("post_count", 0)

            if isinstance(value, (int, float)) and isinstance(post_count, (int, float)) and post_count:
                total_weighted += float(value) * post_count
                total_posts += post_count

        return round(total_weighted / total_posts, 2) if total_posts else None
