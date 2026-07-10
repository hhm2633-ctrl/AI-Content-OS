import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class CompetitorHistory(object):
    """
    Competitor Engine - History.

    storage/competitor/competitor_history.json에 실행별 수집 요약을 append-only로
    기록한다.
    """

    MAX_RECORDS = 500

    def __init__(self, history_path: Optional[Path] = None):
        self.history_path = history_path or Path("storage/competitor/competitor_history.json")
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, profile: Dict[str, Any]) -> None:
        try:
            self._record(profile or {})
        except Exception as error:
            print(f"Competitor History Write Failed: {error}")

    def _record(self, profile: Dict[str, Any]) -> None:
        history = self._load_json()
        records = history.get("records", [])

        if not isinstance(records, list):
            records = []

        records.append({
            "recorded_at": datetime.now().isoformat(),
            "benchmark_files_read": profile.get("benchmark", {}).get("files_read", 0),
            "community_sources": len(profile.get("community", {}).get("sources", [])),
            "news_available": profile.get("news", {}).get("status") == "news_collected",
            "account_profile_count": len(profile.get("account_profiles", [])),
            "tools_funnel_reference_count": len(profile.get("tools_funnel", {}).get("references", [])),
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
