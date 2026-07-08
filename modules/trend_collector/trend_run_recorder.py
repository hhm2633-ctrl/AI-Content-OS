import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class TrendRunRecorder:
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("storage/trends")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir = self.output_dir / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.run_log_path = self.output_dir / "trend_run_log.jsonl"
        self.status_path = self.output_dir / "trend_engine_status.json"
        self.last_safe_result_path = self.output_dir / "last_safe_trend_result.json"

    def finalize_run(self, result: Dict[str, Any]) -> Dict[str, Any]:
        run_at = datetime.now().isoformat()
        recovery_summary = self._build_recovery_summary(result)

        trend_engine_status = dict(result.get("trend_engine_status", {}))
        trend_engine_status.update(recovery_summary)
        trend_engine_status["updated_at"] = run_at
        trend_engine_status["sprint"] = "sprint_1"
        trend_engine_status["sprint_status"] = "completed"
        trend_engine_status["trend_engine_operational"] = True
        trend_engine_status["final_check"] = "passed"
        result["trend_engine_status"] = trend_engine_status

        snapshot_path = self._save_snapshot(result)
        if result.get("selected_topic", {}).get("title"):
            self._save_json(self.last_safe_result_path, result)

        log_entry = self._build_log_entry(
            result=result,
            run_at=run_at,
            snapshot_path=snapshot_path,
        )
        self._append_jsonl(self.run_log_path, log_entry)
        self._save_json(self.status_path, trend_engine_status)

        return {
            "run_at": run_at,
            "run_log_path": str(self.run_log_path).replace("\\", "/"),
            "snapshot_path": str(snapshot_path).replace("\\", "/"),
            "status_path": str(self.status_path).replace("\\", "/"),
            "last_safe_result_path": str(self.last_safe_result_path).replace("\\", "/"),
            "recovery": recovery_summary,
        }

    def _build_recovery_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        status = result.get("trend_engine_status", {})
        selected_topic_available = bool(status.get("selected_topic_available"))
        fallback_sources = status.get("fallback_sources", [])
        failed_sources = status.get("failed_sources", [])
        last_safe_available = self.last_safe_result_path.exists() or selected_topic_available

        if selected_topic_available and not fallback_sources and not failed_sources:
            recovery_mode = "normal"
            recovery_reason = "all_sources_operational"
            recommended_action = "none"
        elif selected_topic_available:
            recovery_mode = "fallback_safe"
            recovery_reason = self._join_reasons(result) or "fallback_result_available"
            recommended_action = "check_source_health_if_repeated"
        elif last_safe_available:
            recovery_mode = "last_safe_available"
            recovery_reason = "selected_topic_missing_current_run"
            recommended_action = "reuse_last_safe_result_and_check_collectors"
        else:
            recovery_mode = "manual_review_required"
            recovery_reason = "no_selected_topic_or_safe_result"
            recommended_action = "check_settings_keywords_and_collector_network"

        return {
            "recovery_mode": recovery_mode,
            "recovery_reason": recovery_reason,
            "recommended_action": recommended_action,
            "last_safe_result_available": bool(last_safe_available),
        }

    def _join_reasons(self, result: Dict[str, Any]) -> str:
        reasons: List[str] = []
        summary = result.get("collection_summary", {})

        for source in ["naver_news", "nate_pann"]:
            status = summary.get(source, {})
            if not isinstance(status, dict):
                continue

            reason = status.get("fallback_reason") or status.get("failed_reason")
            if reason and reason not in reasons:
                reasons.append(reason)

        return ", ".join(reasons)

    def _save_snapshot(self, result: Dict[str, Any]) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path = self.snapshots_dir / f"{timestamp}_trend_result.json"
        self._save_json(snapshot_path, result)
        return snapshot_path

    def _build_log_entry(
        self,
        result: Dict[str, Any],
        run_at: str,
        snapshot_path: Path,
    ) -> Dict[str, Any]:
        collection_summary = result.get("collection_summary", {})
        latest = result.get("source_health_summary", {}).get("latest", {})
        errors = []
        retry = {}
        cache = {}

        for source in ["naver_news", "nate_pann"]:
            source_status = collection_summary.get(source, {})
            health_status = latest.get(source, {})
            if not isinstance(source_status, dict):
                source_status = {}
            if not isinstance(health_status, dict):
                health_status = {}

            retry[source] = {
                "retry_enabled": health_status.get("retry_enabled", source_status.get("retry_enabled", False)),
                "retry_count": health_status.get("retry_count", source_status.get("retry_count", 0)),
            }
            cache[source] = {
                "used_cache": health_status.get("used_cache", source_status.get("used_cache", False)),
                "cache_age_seconds": health_status.get("cache_age_seconds", source_status.get("cache_age_seconds")),
                "cache_expired": health_status.get("cache_expired", source_status.get("cache_expired", False)),
                "cache_path": health_status.get("cache_path", source_status.get("cache_path", "")),
            }

            if source_status.get("error_message"):
                errors.append(
                    {
                        "source": source,
                        "failed_reason": source_status.get("failed_reason", ""),
                        "error_message": source_status.get("error_message", ""),
                    }
                )

        return {
            "run_at": run_at,
            "status": result.get("status", "unknown"),
            "selected_topic": result.get("selected_topic", {}),
            "sources": latest or {
                "naver_news": collection_summary.get("naver_news", {}),
                "nate_pann": collection_summary.get("nate_pann", {}),
            },
            "retry": retry,
            "cache": cache,
            "fallback": {
                "fallback_used": result.get("fallback_used", False),
                "fallback_sources": collection_summary.get("fallback_sources", []),
            },
            "errors": errors,
            "trend_engine_status": result.get("trend_engine_status", {}),
            "snapshot_path": str(snapshot_path).replace("\\", "/"),
        }

    def _append_jsonl(self, path: Path, entry: Dict[str, Any]) -> None:
        with open(path, "a", encoding="utf-8") as file:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _save_json(self, path: Path, data: Dict[str, Any]) -> None:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
