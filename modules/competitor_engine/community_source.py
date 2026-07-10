import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class CommunitySource(object):
    """
    Competitor Engine - Community 소스.

    Trend Collector가 이미 수집해 둔 storage/trends/trend_result.json(읽기 전용,
    own data)에서 커뮤니티 계열 소스(nate_pann/fmkorea/bobaedream)의 수집 상태를
    "커뮤니티 반응 신호"로 재사용한다. 새로운 외부 수집을 하지 않는다.
    """

    COMMUNITY_SOURCES = ["nate_pann", "fmkorea", "bobaedream"]

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        trend_result_path: Optional[Path] = None,
    ):
        self.config = config or {}
        self.trend_result_path = trend_result_path or Path("storage/trends/trend_result.json")

    def collect(self) -> Dict[str, Any]:
        trend_result = self._load_trend_result()
        collection_summary = trend_result.get("collection_summary", {})

        if not isinstance(collection_summary, dict):
            collection_summary = {}

        sources = []

        for source_name in self.COMMUNITY_SOURCES:
            summary = collection_summary.get(source_name)

            if not isinstance(summary, dict):
                continue

            sources.append({
                "source": source_name,
                "success": bool(summary.get("success", False)),
                "count": summary.get("count", 0),
                "collection_method": summary.get("collection_method", ""),
            })

        return {
            "status": "community_collected" if sources else "community_unavailable",
            "sources": sources,
            "fallback_used": not bool(sources),
        }

    def _load_trend_result(self) -> Dict[str, Any]:
        if not self.trend_result_path.exists():
            return {}

        try:
            with open(self.trend_result_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception:
            pass

        return {}
