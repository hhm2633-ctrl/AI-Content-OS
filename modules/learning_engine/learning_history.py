import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class LearningHistory(object):
    """
    Learning Engine - History.

    storage/learning/learning_history.json에 실행별 internal_learning_score/승격
    결과를 append-only로 기록한다.
    """

    MAX_RECORDS = 500

    def __init__(self, history_path: Optional[Path] = None):
        self.history_path = history_path or Path("storage/learning/learning_history.json")
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, internal_learning_score: float, is_good_run: bool, promoted_count: int) -> None:
        try:
            self._record(internal_learning_score, is_good_run, promoted_count)
        except Exception as error:
            print(f"Learning History Write Failed: {error}")

    def _record(self, internal_learning_score: float, is_good_run: bool, promoted_count: int) -> None:
        history = self._load_json()
        records = history.get("records", [])

        if not isinstance(records, list):
            records = []

        records.append({
            "recorded_at": datetime.now().isoformat(),
            "internal_learning_score": internal_learning_score,
            "is_good_run": is_good_run,
            "promoted_count": promoted_count,
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
