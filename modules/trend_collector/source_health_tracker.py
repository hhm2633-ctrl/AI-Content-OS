import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class SourceHealthTracker:
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("storage/trends")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.source_health_path = self.output_dir / "source_health.json"
        self.collector_statistics_path = self.output_dir / "collector_statistics.json"

    def update(self, collection_summary: Dict[str, Any]) -> Dict[str, Any]:
        checked_at = datetime.now().isoformat()
        latest_records = self._build_latest_records(collection_summary, checked_at)

        source_health = self._load_json(
            self.source_health_path,
            {
                "updated_at": None,
                "records": [],
                "latest": {},
            },
        )
        records = source_health.get("records", [])

        if not isinstance(records, list):
            records = []

        records.extend(latest_records)

        latest = {
            record["source"]: record
            for record in latest_records
        }
        source_health = {
            "updated_at": checked_at,
            "records": records,
            "latest": {
                **source_health.get("latest", {}),
                **latest,
            },
        }
        self._save_json(self.source_health_path, source_health)

        collector_statistics = self._update_statistics(latest_records, checked_at)
        self._save_json(self.collector_statistics_path, collector_statistics)

        return {
            "updated_at": checked_at,
            "source_health_path": str(self.source_health_path).replace("\\", "/"),
            "collector_statistics_path": str(self.collector_statistics_path).replace("\\", "/"),
            "latest": latest,
            "statistics": collector_statistics.get("sources", []),
        }

    def _build_latest_records(
        self,
        collection_summary: Dict[str, Any],
        checked_at: str,
    ) -> List[Dict[str, Any]]:
        records = []

        for source in ["naver_news", "nate_pann"]:
            status = collection_summary.get(source, {})

            if not isinstance(status, dict):
                status = {}

            records.append(
                {
                    "source": status.get("source", source),
                    "attempted": bool(status.get("attempted", False)),
                    "success": bool(status.get("success", False)),
                    "count": int(status.get("count", 0) or 0),
                    "failed_reason": status.get("failed_reason", ""),
                    "fallback_reason": status.get("fallback_reason", ""),
                    "collection_method": status.get("collection_method", ""),
                    "used_cache": bool(status.get("used_cache", False)),
                    "cache_path": status.get("cache_path", ""),
                    "retry_enabled": bool(status.get("retry_enabled", False)),
                    "retry_count": int(status.get("retry_count", 0) or 0),
                    "cache_age_seconds": status.get("cache_age_seconds"),
                    "cache_expired": bool(status.get("cache_expired", False)),
                    "checked_at": checked_at,
                }
            )

        return records

    def _update_statistics(
        self,
        latest_records: List[Dict[str, Any]],
        checked_at: str,
    ) -> Dict[str, Any]:
        existing = self._load_json(
            self.collector_statistics_path,
            {
                "updated_at": None,
                "sources": [],
            },
        )
        source_map = {}

        for item in existing.get("sources", []):
            if isinstance(item, dict) and item.get("source"):
                source_map[item["source"]] = item

        for record in latest_records:
            source = record["source"]
            stats = source_map.get(
                source,
                {
                    "source": source,
                    "total_attempts": 0,
                    "total_success": 0,
                    "total_failures": 0,
                    "last_success_at": None,
                    "last_failure_at": None,
                    "last_failed_reason": "",
                    "last_collection_method": "",
                    "total_fallback_used": 0,
                },
            )

            if record.get("attempted", False):
                stats["total_attempts"] = int(stats.get("total_attempts", 0)) + 1

                if record.get("success", False):
                    stats["total_success"] = int(stats.get("total_success", 0)) + 1
                    stats["last_success_at"] = checked_at
                else:
                    stats["total_failures"] = int(stats.get("total_failures", 0)) + 1
                    stats["last_failure_at"] = checked_at
                    stats["last_failed_reason"] = record.get("failed_reason", "")

            if self._record_used_fallback(record):
                stats["total_fallback_used"] = int(stats.get("total_fallback_used", 0)) + 1

            stats["last_collection_method"] = record.get("collection_method", "")
            source_map[source] = stats

        return {
            "updated_at": checked_at,
            "sources": sorted(
                source_map.values(),
                key=lambda item: item.get("source", ""),
            ),
        }

    def _record_used_fallback(self, record: Dict[str, Any]) -> bool:
        collection_method = str(record.get("collection_method", ""))

        return bool(
            record.get("fallback_reason")
            or record.get("used_cache")
            or "fallback" in collection_method
            or collection_method.endswith("_cache")
        )

    def _load_json(self, path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        if not path.exists():
            return default

        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data

        except Exception:
            pass

        return default

    def _save_json(self, path: Path, data: Dict[str, Any]) -> None:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
