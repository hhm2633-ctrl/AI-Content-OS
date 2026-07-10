import json
from pathlib import Path
from typing import Any, Dict, Optional


class NewsSource(object):
    """
    Competitor Engine - News 소스.

    storage/trends/trend_result.json(읽기 전용, own data)의 naver_news 수집
    상태를 "뉴스 화제성 신호"로 재사용한다. 새로운 외부 수집을 하지 않는다.
    """

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

        naver_news = collection_summary.get("naver_news")

        if not isinstance(naver_news, dict):
            return {"status": "news_unavailable", "source": {}, "fallback_used": True}

        return {
            "status": "news_collected",
            "source": {
                "source": "naver_news",
                "success": bool(naver_news.get("success", False)),
                "count": naver_news.get("count", 0),
                "collection_method": naver_news.get("collection_method", ""),
            },
            "fallback_used": False,
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
