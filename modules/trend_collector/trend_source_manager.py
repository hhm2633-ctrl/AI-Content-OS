import json
from pathlib import Path
from typing import Any, Dict, List

from modules.trend_collector.nate_pann_collector import NatePannCollector
from modules.trend_collector.naver_news_collector import NaverNewsCollector


class TrendSourceManager:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.source_config = self._load_source_config()
        self.nate_pann_collector = NatePannCollector()
        self.naver_news_collector = NaverNewsCollector()
        self.last_collection_summary = self._empty_collection_summary()

    def _empty_collection_summary(self) -> Dict[str, Any]:
        return {
            "naver_news": {
                "attempted": False,
                "success": False,
                "count": 0,
            },
            "nate_pann": {
                "attempted": False,
                "success": False,
                "count": 0,
            },
            "fallback_used": False,
            "fallback_sources": [],
        }

    def _load_source_config(self) -> Dict[str, Any]:
        config_path = Path("config/trend_sources.json")

        if not config_path.exists():
            return self._fallback_source_config()

        try:
            with open(config_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return self._fallback_source_config()

    def _fallback_source_config(self) -> Dict[str, Any]:
        return {
            "sources": [
                {
                    "source_id": "naver_news",
                    "name": "Naver News",
                    "enabled": True,
                    "tier": 1,
                    "weight": 30,
                    "type": "news",
                },
                {
                    "source_id": "manual",
                    "name": "Manual Fallback",
                    "enabled": True,
                    "tier": 99,
                    "weight": 5,
                    "type": "manual",
                },
            ]
        }

    def get_enabled_sources(self) -> List[Dict[str, Any]]:
        sources = self.source_config.get("sources", [])
        enabled_sources = []

        for source in sources:
            if isinstance(source, dict) and source.get("enabled", False):
                enabled_sources.append(source)

        enabled_sources.sort(
            key=lambda item: (
                int(item.get("tier", 99)),
                -int(item.get("weight", 0)),
            )
        )

        return enabled_sources

    def collect_from_enabled_sources(self) -> List[Dict[str, Any]]:
        enabled_sources = self.get_enabled_sources()
        collected = []
        self.last_collection_summary = self._empty_collection_summary()

        for source in enabled_sources:
            source_id = source.get("source_id", "unknown")

            if source_id == "naver_news":
                collected.extend(self._collect_naver_news(source))
                continue

            if source_id == "nate_pann":
                nate_results = self._collect_nate_pann(source)

                if nate_results:
                    collected.extend(nate_results)
                else:
                    self._mark_fallback("nate_pann")
                    collected.extend(self._placeholder_collect(source))
                continue

            if source_id == "manual":
                if not collected:
                    collected.extend(self.build_manual_trends())
                continue

            collected.extend(self._placeholder_collect(source))

        if not collected:
            collected = self.build_manual_trends()

        return collected

    def _collect_naver_news(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        print("Naver News Collect Started")
        self.last_collection_summary["naver_news"]["attempted"] = True

        query_keywords = self.config.get("naver_news_keywords", [])

        if not query_keywords:
            query_keywords = [
                "AI automation",
                "content automation",
                "Instagram monetization",
                "smart store",
            ]

        results = self.naver_news_collector.collect(
            query_keywords=query_keywords,
            source=source,
        )

        self.last_collection_summary["naver_news"]["count"] = len(results)
        self.last_collection_summary["naver_news"]["success"] = bool(results)

        if not results:
            print("Naver News Empty. Other sources or manual fallback will be used.")

        print("Naver News Collect Finished")
        return results

    def _collect_nate_pann(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        print("Nate Pann Collect Started")
        self.last_collection_summary["nate_pann"]["attempted"] = True

        results = self.nate_pann_collector.collect(source=source)

        self.last_collection_summary["nate_pann"]["count"] = len(results)
        self.last_collection_summary["nate_pann"]["success"] = bool(results)

        if not results:
            print("Nate Pann Empty. Placeholder fallback will be used.")

        print("Nate Pann Collect Finished")
        return results

    def build_manual_trends(self) -> List[Dict[str, Any]]:
        self._mark_fallback("manual")
        manual_keywords = self.config.get("trend_sources", [])

        if not manual_keywords:
            manual_keywords = [
                "AI automation",
                "Instagram card news",
                "content automation",
                "blog automation",
            ]

        trends = []

        for index, keyword in enumerate(manual_keywords, start=1):
            trends.append(
                {
                    "keyword": keyword,
                    "source_id": "manual",
                    "source_name": "Manual Fallback",
                    "source_type": "manual",
                    "tier": 99,
                    "weight": 5,
                    "base_score": 100 - index,
                    "trend_reason": "settings.json fallback keyword",
                    "collection_method": "settings_fallback",
                    "is_fallback": True,
                }
            )

        return trends

    def _placeholder_collect(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        source_id = source.get("source_id", "unknown")
        source_name = source.get("name", source_id)
        source_type = source.get("type", "unknown")
        tier = int(source.get("tier", 99))
        weight = int(source.get("weight", 0))

        keyword_map = {
            "nate_pann": [
                "side income concern",
                "career change preparation",
                "living cost concern",
            ],
            "bobaedream": [
                "self employment reality",
                "inflation concern",
                "online sales concern",
            ],
            "fmkorea": [
                "AI content trend",
                "Instagram algorithm",
                "side hustle monetization",
            ],
            "dcinside": [
                "AI image automation",
                "blog automation",
                "content repeat workflow",
            ],
            "ppomppu": [
                "saving money",
                "living cost reduction",
                "discount trend",
            ],
            "google_trends": [
                "AI content",
                "side income recommendation",
                "Instagram monetization",
            ],
            "youtube": [
                "AI side hustle",
                "faceless income",
                "card news creation",
            ],
            "reddit": [
                "AI automation tools",
                "content workflow",
                "side hustle automation",
            ],
            "x": [
                "AI trend",
                "creator economy",
                "automation workflow",
            ],
        }

        keywords = keyword_map.get(source_id, [])
        trends = []

        if keywords:
            self._mark_fallback(source_id)

        for index, keyword in enumerate(keywords, start=1):
            trends.append(
                {
                    "keyword": keyword,
                    "source_id": source_id,
                    "source_name": source_name,
                    "source_type": source_type,
                    "tier": tier,
                    "weight": weight,
                    "base_score": 100 - index,
                    "trend_reason": f"{source_name} placeholder trend",
                    "collection_method": "placeholder_fallback",
                    "is_fallback": True,
                }
            )

        return trends

    def _mark_fallback(self, source_id: str) -> None:
        self.last_collection_summary["fallback_used"] = True

        fallback_sources = self.last_collection_summary["fallback_sources"]
        if source_id not in fallback_sources:
            fallback_sources.append(source_id)
