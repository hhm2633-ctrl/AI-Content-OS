import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class AnalyticsHistory(object):
    """
    Analytics Engine - History (Sprint 13).

    storage/analytics/analytics_history.json에 실행별 내부 품질 추세 판정을
    append-only로 기록한다 (실측/허구 구분 없이, 전부 로컬에서 실제로 계산된 값).
    """

    MAX_RECORDS = 500

    def __init__(self, history_path: Optional[Path] = None):
        self.history_path = history_path or Path("storage/analytics/analytics_history.json")
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, trend_result: Dict[str, Any]) -> None:
        try:
            self._record(trend_result or {})
        except Exception as error:
            print(f"Analytics History Write Failed: {error}")

    def _record(self, trend_result: Dict[str, Any]) -> None:
        history = self._load_json()
        records = history.get("records", [])

        if not isinstance(records, list):
            records = []

        records.append({
            "recorded_at": datetime.now().isoformat(),
            "current_performance_score": trend_result.get("current_performance_score", 0.0),
            "current_audit_score": trend_result.get("current_audit_score", 0.0),
            "historical_average_performance_score": trend_result.get("historical_average_performance_score"),
            "quality_trend": trend_result.get("quality_trend", "insufficient_history"),
        })

        if len(records) > self.MAX_RECORDS:
            records = records[-self.MAX_RECORDS:]

        self._save_json({"updated_at": datetime.now().isoformat(), "records": records})

    def _load_json(self) -> Dict[str, Any]:
        if not self.history_path.exists():
            return {"updated_at": None, "records": []}

        try:
            with open(self.history_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception:
            pass

        return {"updated_at": None, "records": []}

    def _save_json(self, data: Dict[str, Any]) -> None:
        with open(self.history_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
