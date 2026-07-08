import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from modules.trend_collector.nate_pann_collector import NatePannCollector
from modules.trend_collector.naver_news_collector import NaverNewsCollector
from modules.trend_collector.retry_policy import RetryPolicy


class TrendSourceManager:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.source_config = self._load_source_config()
        self.nate_pann_collector = NatePannCollector()
        self.naver_news_collector = NaverNewsCollector()
        trend_config = self.config.get("trend_collector", {})
        self.cache_ttl_seconds = int(trend_config.get("cache_ttl_seconds", 24 * 60 * 60))
        self.retry_policy = RetryPolicy(
            enabled=bool(trend_config.get("retry_enabled", True)),
            max_retries=int(trend_config.get("max_retries", 2)),
            delay_seconds=float(trend_config.get("retry_delay_seconds", 0.5)),
        )
        self.cache_dir = Path("storage/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.naver_news_cache_path = self.cache_dir / "naver_news_cache.json"
        self.nate_pann_cache_path = self.cache_dir / "nate_pann_cache.json"
        self._ensure_naver_news_cache_file()
        self._ensure_nate_pann_cache_file()
        self.last_collection_summary = self._empty_collection_summary()

    def _empty_collection_summary(self) -> Dict[str, Any]:
        return {
            "naver_news": {
                "source": "naver_news",
                "attempted": False,
                "success": False,
                "count": 0,
                "error_message": "",
                "failed_reason": "",
                "fallback_reason": "",
                "collection_method": "",
                "used_cache": False,
                "cache_path": str(self.naver_news_cache_path).replace("\\", "/"),
                "retry_enabled": self.retry_policy.enabled,
                "retry_count": 0,
                "cache_age_seconds": None,
                "cache_expired": False,
            },
            "nate_pann": {
                "source": "nate_pann",
                "attempted": False,
                "success": False,
                "count": 0,
                "error_message": "",
                "failed_reason": "",
                "fallback_reason": "",
                "collection_method": "",
                "used_cache": False,
                "cache_path": str(self.nate_pann_cache_path).replace("\\", "/"),
                "retry_enabled": self.retry_policy.enabled,
                "retry_count": 0,
                "cache_age_seconds": None,
                "cache_expired": False,
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
                collected.extend(self._collect_nate_pann(source))
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

        query_keywords = self.config.get("naver_news_keywords", [])

        if not query_keywords:
            query_keywords = [
                "AI automation",
                "content automation",
                "Instagram monetization",
                "smart store",
            ]

        results, collector_status = self.retry_policy.run_collect(
            collect_fn=lambda: self.naver_news_collector.collect(
                query_keywords=query_keywords,
                source=source,
            ),
            status_fn=lambda: self.naver_news_collector.last_status,
        )
        self._update_naver_news_summary(collector_status)

        if results:
            self._save_naver_news_cache(results)
            print("Naver News Collect Finished")
            return results

        cache_results = self._load_naver_news_cache(source)

        if cache_results:
            cache_meta = self._cache_meta(self.naver_news_cache_path)
            fallback_reason = collector_status.get("failed_reason") or "no_results"
            self._mark_fallback("naver_news_cache")
            self._update_naver_news_summary(
                {
                    **collector_status,
                    "count": len(cache_results),
                    "fallback_reason": fallback_reason,
                    "collection_method": "naver_news_cache",
                    "used_cache": True,
                    "cache_age_seconds": cache_meta["cache_age_seconds"],
                    "cache_expired": cache_meta["cache_expired"],
                }
            )
            print("Naver News Cache Fallback Used")
            print("Naver News Collect Finished")
            return cache_results

        settings_results = self._build_naver_settings_fallback(
            source=source,
            query_keywords=query_keywords,
            fallback_reason=collector_status.get("failed_reason") or "no_results",
        )

        if settings_results:
            self._mark_fallback("naver_news_settings")
            self._update_naver_news_summary(
                {
                    **collector_status,
                    "count": len(settings_results),
                    "fallback_reason": collector_status.get("failed_reason") or "no_results",
                    "collection_method": "settings_keyword_fallback",
                    "used_cache": False,
                }
            )
            print("Naver News Settings Keyword Fallback Used")
            print("Naver News Collect Finished")
            return settings_results

        placeholder_results = self._build_naver_placeholder_fallback(
            source=source,
            fallback_reason=collector_status.get("failed_reason") or "no_results",
        )

        self._mark_fallback("naver_news_placeholder")
        self._update_naver_news_summary(
            {
                **collector_status,
                "count": len(placeholder_results),
                "fallback_reason": collector_status.get("failed_reason") or "no_results",
                "collection_method": "placeholder_fallback",
                "used_cache": False,
            }
        )
        print("Naver News Placeholder Fallback Used")

        print("Naver News Collect Finished")
        return placeholder_results

    def _collect_nate_pann(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        print("Nate Pann Collect Started")

        results, collector_status = self.retry_policy.run_collect(
            collect_fn=lambda: self.nate_pann_collector.collect(source=source),
            status_fn=lambda: self.nate_pann_collector.last_status,
        )
        self._update_nate_pann_summary(collector_status)

        if results:
            self._save_nate_pann_cache(results)
            print("Nate Pann Collect Finished")
            return results

        cache_results = self._load_nate_pann_cache(source)

        if cache_results:
            cache_meta = self._cache_meta(self.nate_pann_cache_path)
            fallback_reason = collector_status.get("failed_reason") or "empty_result"
            self._mark_fallback("nate_pann_cache")
            self._update_nate_pann_summary(
                {
                    **collector_status,
                    "count": len(cache_results),
                    "fallback_reason": fallback_reason,
                    "collection_method": "nate_pann_cache",
                    "used_cache": True,
                    "cache_age_seconds": cache_meta["cache_age_seconds"],
                    "cache_expired": cache_meta["cache_expired"],
                }
            )
            print("Nate Pann Cache Fallback Used")
            print("Nate Pann Collect Finished")
            return cache_results

        settings_results = self._build_nate_pann_settings_fallback(
            source=source,
            fallback_reason=collector_status.get("failed_reason") or "empty_result",
        )

        if settings_results:
            self._mark_fallback("nate_pann_settings")
            self._update_nate_pann_summary(
                {
                    **collector_status,
                    "count": len(settings_results),
                    "fallback_reason": collector_status.get("failed_reason") or "empty_result",
                    "collection_method": "settings_keyword_fallback",
                    "used_cache": False,
                }
            )
            print("Nate Pann Settings Keyword Fallback Used")
            print("Nate Pann Collect Finished")
            return settings_results

        placeholder_results = self._build_nate_pann_placeholder_fallback(
            source=source,
            fallback_reason=collector_status.get("failed_reason") or "empty_result",
        )

        self._mark_fallback("nate_pann_placeholder")
        self._update_nate_pann_summary(
            {
                **collector_status,
                "count": len(placeholder_results),
                "fallback_reason": collector_status.get("failed_reason") or "empty_result",
                "collection_method": "placeholder_fallback",
                "used_cache": False,
            }
        )
        print("Nate Pann Placeholder Fallback Used")

        print("Nate Pann Collect Finished")
        return placeholder_results

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
                    "collection_method": "settings_keyword_fallback",
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

    def _ensure_naver_news_cache_file(self) -> None:
        if self.naver_news_cache_path.exists():
            return

        self._write_json(
            self.naver_news_cache_path,
            {
                "source": "naver_news",
                "updated_at": None,
                "count": 0,
                "items": [],
            },
        )

    def _ensure_nate_pann_cache_file(self) -> None:
        if self.nate_pann_cache_path.exists():
            return

        self._write_json(
            self.nate_pann_cache_path,
            {
                "source": "nate_pann",
                "updated_at": None,
                "count": 0,
                "items": [],
            },
        )

    def _save_naver_news_cache(self, results: List[Dict[str, Any]]) -> None:
        cache_items = []

        for item in results:
            cache_item = dict(item)
            cache_item["collection_method"] = "naver_news_cache"
            cache_item["is_fallback"] = True
            cache_items.append(cache_item)

        self._write_json(
            self.naver_news_cache_path,
            {
                "source": "naver_news",
                "updated_at": self._now(),
                "count": len(cache_items),
                "items": cache_items,
            },
        )

    def _load_naver_news_cache(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        data = self._read_json(self.naver_news_cache_path)
        items = data.get("items", [])

        if not isinstance(items, list) or not items:
            return []

        cache_results = []

        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue

            cache_item = dict(item)
            cache_item["source_id"] = "naver_news"
            cache_item["source_name"] = source.get("name", "Naver News")
            cache_item["source_type"] = source.get("type", "news")
            cache_item["tier"] = int(source.get("tier", 1))
            cache_item["weight"] = int(source.get("weight", 30))
            cache_item["base_score"] = int(cache_item.get("base_score", 110 - index))
            cache_item["collection_method"] = "naver_news_cache"
            cache_item["is_fallback"] = True
            cache_item["trend_reason"] = "Naver News cache fallback"
            cache_item["collected_at"] = self._now()
            cache_results.append(cache_item)

        return cache_results

    def _save_nate_pann_cache(self, results: List[Dict[str, Any]]) -> None:
        cache_items = []

        for item in results:
            cache_item = dict(item)
            cache_item["collection_method"] = "nate_pann_cache"
            cache_item["is_fallback"] = True
            cache_items.append(cache_item)

        self._write_json(
            self.nate_pann_cache_path,
            {
                "source": "nate_pann",
                "updated_at": self._now(),
                "count": len(cache_items),
                "items": cache_items,
            },
        )

    def _load_nate_pann_cache(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        data = self._read_json(self.nate_pann_cache_path)
        items = data.get("items", [])

        if not isinstance(items, list) or not items:
            return []

        cache_results = []

        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue

            cache_item = dict(item)
            cache_item["source_id"] = "nate_pann"
            cache_item["source_name"] = source.get("name", "Nate Pann")
            cache_item["source_type"] = source.get("type", "community")
            cache_item["tier"] = int(source.get("tier", 1))
            cache_item["weight"] = int(source.get("weight", 30))
            cache_item["base_score"] = int(cache_item.get("base_score", 110 - index))
            cache_item["collection_method"] = "nate_pann_cache"
            cache_item["is_fallback"] = True
            cache_item["trend_reason"] = "Nate Pann cache fallback"
            cache_item["collected_at"] = self._now()
            cache_results.append(cache_item)

        return cache_results

    def _build_naver_settings_fallback(
        self,
        source: Dict[str, Any],
        query_keywords: List[str],
        fallback_reason: str,
    ) -> List[Dict[str, Any]]:
        fallback_keywords = query_keywords or self.config.get("trend_sources", [])

        if not fallback_keywords:
            return []

        results = []

        for index, keyword in enumerate(fallback_keywords, start=1):
            results.append(
                {
                    "keyword": keyword,
                    "link": "",
                    "summary": "",
                    "publisher": "",
                    "published_at": "",
                    "query": keyword,
                    "source_id": "naver_news",
                    "source_name": source.get("name", "Naver News"),
                    "source_type": source.get("type", "news"),
                    "tier": int(source.get("tier", 1)),
                    "weight": int(source.get("weight", 30)),
                    "base_score": 105 - index,
                    "trend_reason": f"Naver News settings fallback: {fallback_reason}",
                    "collection_method": "settings_keyword_fallback",
                    "is_fallback": True,
                    "collected_at": self._now(),
                }
            )

        return results

    def _build_naver_placeholder_fallback(
        self,
        source: Dict[str, Any],
        fallback_reason: str,
    ) -> List[Dict[str, Any]]:
        keywords = [
            "AI content automation",
            "creator economy",
            "Instagram monetization",
            "workflow automation",
        ]
        results = []

        for index, keyword in enumerate(keywords, start=1):
            results.append(
                {
                    "keyword": keyword,
                    "link": "",
                    "summary": "",
                    "publisher": "",
                    "published_at": "",
                    "query": "",
                    "source_id": "naver_news",
                    "source_name": source.get("name", "Naver News"),
                    "source_type": source.get("type", "news"),
                    "tier": int(source.get("tier", 1)),
                    "weight": int(source.get("weight", 30)),
                    "base_score": 95 - index,
                    "trend_reason": f"Naver News placeholder fallback: {fallback_reason}",
                    "collection_method": "placeholder_fallback",
                    "is_fallback": True,
                    "collected_at": self._now(),
                }
            )

        return results

    def _build_nate_pann_settings_fallback(
        self,
        source: Dict[str, Any],
        fallback_reason: str,
    ) -> List[Dict[str, Any]]:
        fallback_keywords = self.config.get("trend_sources", [])

        if not fallback_keywords:
            return []

        results = []

        for index, keyword in enumerate(fallback_keywords, start=1):
            results.append(
                {
                    "keyword": keyword,
                    "link": "",
                    "summary": "",
                    "publisher": "settings.json",
                    "published_at": "",
                    "query": keyword,
                    "source_id": "nate_pann",
                    "source_name": source.get("name", "Nate Pann"),
                    "source_type": source.get("type", "community"),
                    "tier": int(source.get("tier", 1)),
                    "weight": int(source.get("weight", 30)),
                    "base_score": 103 - index,
                    "trend_reason": f"Nate Pann settings fallback: {fallback_reason}",
                    "collection_method": "settings_keyword_fallback",
                    "is_fallback": True,
                    "collected_at": self._now(),
                }
            )

        return results

    def _build_nate_pann_placeholder_fallback(
        self,
        source: Dict[str, Any],
        fallback_reason: str,
    ) -> List[Dict[str, Any]]:
        keywords = [
            "side income concern",
            "career change preparation",
            "living cost concern",
        ]
        results = []

        for index, keyword in enumerate(keywords, start=1):
            results.append(
                {
                    "keyword": keyword,
                    "link": "",
                    "summary": "",
                    "publisher": "",
                    "published_at": "",
                    "query": "",
                    "source_id": "nate_pann",
                    "source_name": source.get("name", "Nate Pann"),
                    "source_type": source.get("type", "community"),
                    "tier": int(source.get("tier", 1)),
                    "weight": int(source.get("weight", 30)),
                    "base_score": 95 - index,
                    "trend_reason": f"Nate Pann placeholder fallback: {fallback_reason}",
                    "collection_method": "placeholder_fallback",
                    "is_fallback": True,
                    "collected_at": self._now(),
                }
            )

        return results

    def _update_naver_news_summary(self, status: Dict[str, Any]) -> None:
        summary = self.last_collection_summary["naver_news"]
        summary.update(
            {
                "source": "naver_news",
                "attempted": bool(status.get("attempted", summary.get("attempted"))),
                "success": bool(status.get("success", summary.get("success"))),
                "count": int(status.get("count", summary.get("count", 0))),
                "error_message": status.get("error_message", summary.get("error_message", "")),
                "failed_reason": status.get("failed_reason", summary.get("failed_reason", "")),
                "fallback_reason": status.get("fallback_reason", summary.get("fallback_reason", "")),
                "collection_method": status.get("collection_method", summary.get("collection_method", "")),
                "used_cache": bool(status.get("used_cache", summary.get("used_cache", False))),
                "cache_path": str(self.naver_news_cache_path).replace("\\", "/"),
                "retry_enabled": bool(status.get("retry_enabled", summary.get("retry_enabled", self.retry_policy.enabled))),
                "retry_count": int(status.get("retry_count", summary.get("retry_count", 0)) or 0),
                "cache_age_seconds": status.get("cache_age_seconds", summary.get("cache_age_seconds")),
                "cache_expired": bool(status.get("cache_expired", summary.get("cache_expired", False))),
            }
        )

    def _update_nate_pann_summary(self, status: Dict[str, Any]) -> None:
        summary = self.last_collection_summary["nate_pann"]
        summary.update(
            {
                "source": "nate_pann",
                "attempted": bool(status.get("attempted", summary.get("attempted"))),
                "success": bool(status.get("success", summary.get("success"))),
                "count": int(status.get("count", summary.get("count", 0))),
                "error_message": status.get("error_message", summary.get("error_message", "")),
                "failed_reason": status.get("failed_reason", summary.get("failed_reason", "")),
                "fallback_reason": status.get("fallback_reason", summary.get("fallback_reason", "")),
                "collection_method": status.get("collection_method", summary.get("collection_method", "")),
                "used_cache": bool(status.get("used_cache", summary.get("used_cache", False))),
                "cache_path": str(self.nate_pann_cache_path).replace("\\", "/"),
                "retry_enabled": bool(status.get("retry_enabled", summary.get("retry_enabled", self.retry_policy.enabled))),
                "retry_count": int(status.get("retry_count", summary.get("retry_count", 0)) or 0),
                "cache_age_seconds": status.get("cache_age_seconds", summary.get("cache_age_seconds")),
                "cache_expired": bool(status.get("cache_expired", summary.get("cache_expired", False))),
            }
        )

    def _cache_meta(self, path: Path) -> Dict[str, Any]:
        data = self._read_json(path)
        updated_at = data.get("updated_at")
        age_seconds = self._cache_age_seconds(updated_at)

        return {
            "cache_age_seconds": age_seconds,
            "cache_expired": (
                bool(age_seconds is not None and age_seconds > self.cache_ttl_seconds)
            ),
        }

    def _cache_age_seconds(self, updated_at: Any) -> Any:
        if not updated_at:
            return None

        try:
            updated = datetime.fromisoformat(str(updated_at))
            return max(0, int((datetime.now() - updated).total_seconds()))
        except Exception:
            return None

    def _read_json(self, path: Path) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception:
            pass

        return {}

    def _write_json(self, path: Path, data: Dict[str, Any]) -> None:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def _now(self) -> str:
        from datetime import datetime

        return datetime.now().isoformat()
