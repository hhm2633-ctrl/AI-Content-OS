import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class TrendMemoryStorage(object):
    """
    Trend Memory - Storage.

    storage/trend_memory/trend_memory.json에 최근 생성된 Topic/Hook/CTA/Layout/Image
    조합을 누적 기록한다(최근 MAX_RECORDS건만 유지). 파일이 없거나 손상되어도
    빈 기록으로 취급한다.
    """

    MAX_RECORDS = 200

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("storage/trend_memory")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.memory_path = self.output_dir / "trend_memory.json"

    def load_recent(self, limit: int = 30) -> List[Dict[str, Any]]:
        data = self._load_json()
        records = data.get("records", [])

        if not isinstance(records, list):
            return []

        return records[-limit:]

    def append(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        data = self._load_json()
        records = data.get("records", [])

        if not isinstance(records, list):
            records = []

        records.append(entry)

        if len(records) > self.MAX_RECORDS:
            records = records[-self.MAX_RECORDS:]

        result = {
            "updated_at": datetime.now().isoformat(),
            "total_count": len(records),
            "records": records,
        }

        self._save_json(result)
        return result

    def _load_json(self) -> Dict[str, Any]:
        if not self.memory_path.exists():
            return {"updated_at": None, "total_count": 0, "records": []}

        try:
            with open(self.memory_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception:
            pass

        return {"updated_at": None, "total_count": 0, "records": []}

    def _save_json(self, data: Dict[str, Any]) -> None:
        with open(self.memory_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
