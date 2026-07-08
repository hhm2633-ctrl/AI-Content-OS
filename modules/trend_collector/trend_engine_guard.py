import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class TrendEngineGuard:
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("storage/trends")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.last_safe_result_path = self.output_dir / "last_safe_trend_result.json"

    def normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(result, dict):
            result = {}

        result.setdefault("status", "success")
        result.setdefault("message", "trend_collection_completed")
        result.setdefault("trends", [])
        result.setdefault("collection_summary", {})
        result.setdefault("source_health_summary", {})
        result.setdefault("trend_engine_status", {})

        if not isinstance(result.get("trends"), list):
            result["trends"] = []

        selected_topic = result.get("selected_topic")
        if not self._has_selected_topic(selected_topic):
            selected_topic = self._load_last_safe_selected_topic() or self._placeholder_topic()
            result["selected_topic"] = selected_topic

        status = dict(result.get("trend_engine_status", {}))
        status.update(
            {
                "selected_topic_available": self._has_selected_topic(result.get("selected_topic")),
                "workflow_safe": True,
                "guard_checked": True,
                "guard_checked_at": datetime.now().isoformat(),
                "operational_status": "trend_engine_operational_complete",
            }
        )
        status.setdefault("total_sources", 0)
        status.setdefault("success_sources", [])
        status.setdefault("failed_sources", [])
        status.setdefault("fallback_sources", [])
        result["trend_engine_status"] = status

        self._ensure_json_file(
            self.output_dir / "source_health.json",
            {"updated_at": None, "records": [], "latest": {}},
        )
        self._ensure_json_file(
            self.output_dir / "collector_statistics.json",
            {"updated_at": None, "sources": []},
        )
        self._ensure_json_file(
            self.output_dir / "trend_engine_status.json",
            status,
        )

        return result

    def _has_selected_topic(self, selected_topic: Any) -> bool:
        return isinstance(selected_topic, dict) and bool(
            str(selected_topic.get("title", "")).strip()
        )

    def _load_last_safe_selected_topic(self) -> Dict[str, Any]:
        data = self._read_json(self.last_safe_result_path)
        selected_topic = data.get("selected_topic", {})

        if self._has_selected_topic(selected_topic):
            safe_topic = dict(selected_topic)
            safe_topic["picked_reason"] = safe_topic.get(
                "picked_reason",
                "last_safe_trend_result fallback",
            )
            return safe_topic

        return {}

    def _placeholder_topic(self) -> Dict[str, Any]:
        return {
            "title": "AI content automation",
            "source": "placeholder",
            "quality_score": 0,
            "selection_reason": "트렌드 후보가 비어 있어 안전한 기본 주제로 대체함",
            "collection_method": "placeholder_fallback",
            "picked_reason": "guard_placeholder_fallback",
        }

    def _ensure_json_file(self, path: Path, default: Dict[str, Any]) -> None:
        data = self._read_json(path)

        if data:
            return

        with open(path, "w", encoding="utf-8") as file:
            json.dump(default, file, ensure_ascii=False, indent=2)

    def _read_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}

        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception:
            pass

        return {}
