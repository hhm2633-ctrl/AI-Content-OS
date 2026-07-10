import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class PerformanceScoreHistory(object):
    """
    Performance Score - History.

    storage/performance_score/performance_score_history.json에 실행별 점수를
    append-only로 기록한다 (다른 Engine들의 history 파일과 동일한 규칙).
    """

    MAX_RECORDS = 500

    def __init__(self, history_path: Optional[Path] = None):
        self.history_path = history_path or Path("storage/performance_score/performance_score_history.json")
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, scores: Dict[str, Any]) -> None:
        try:
            self._record(scores or {})
        except Exception as error:
            print(f"Performance Score History Write Failed: {error}")

    def _record(self, scores: Dict[str, Any]) -> None:
        history = self._load_json()
        records = history.get("records", [])

        if not isinstance(records, list):
            records = []

        records.append({
            "recorded_at": datetime.now().isoformat(),
            **{
                field: scores.get(field)
                for field in (
                    "hook_score", "cta_score", "layout_score",
                    "brand_score", "image_score", "overall_performance_score",
                )
            },
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
