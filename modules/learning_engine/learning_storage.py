import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class LearningStorage(object):
    """
    Learning Engine - Storage / Memory.

    storage/learning/learning_memory.json에 "검증된 고성과 패턴"만 knowledge_id
    기준으로 누적 저장한다 (전체 Knowledge DB의 부분집합). 같은 항목이 다시 좋은
    실행에서 선택되면 reinforced_count/memory_score를 올려 반복 검증된 패턴임을
    표시한다.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("storage/learning")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.memory_path = self.output_dir / "learning_memory.json"
        self.statistics_path = self.output_dir / "learning_statistics.json"

    def load_memory(self) -> List[Dict[str, Any]]:
        data = self._load_json(self.memory_path, {"updated_at": None, "records": []})
        records = data.get("records", [])
        return records if isinstance(records, list) else []

    def upsert_memory(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        existing = self.load_memory()
        by_id = {
            record.get("knowledge_id"): record
            for record in existing
            if isinstance(record, dict) and record.get("knowledge_id")
        }

        for entry in entries or []:
            knowledge_id = entry.get("knowledge_id")

            if not knowledge_id:
                continue

            by_id[knowledge_id] = entry

        merged = list(by_id.values())

        self._save_json(self.memory_path, {
            "updated_at": datetime.now().isoformat(),
            "total_count": len(merged),
            "records": merged,
        })

        return {"total_count": len(merged)}

    def update_statistics(self, is_good_run: bool, promoted_count: int) -> Dict[str, Any]:
        statistics = self._load_json(self.statistics_path, self._empty_statistics())

        statistics["total_runs"] = int(statistics.get("total_runs", 0)) + 1

        if is_good_run:
            statistics["total_good_runs"] = int(statistics.get("total_good_runs", 0)) + 1

        statistics["total_promoted"] = int(statistics.get("total_promoted", 0)) + int(promoted_count)
        statistics["total_memory_count"] = len(self.load_memory())
        statistics["updated_at"] = datetime.now().isoformat()

        self._save_json(self.statistics_path, statistics)
        return statistics

    def load_statistics(self) -> Dict[str, Any]:
        return self._load_json(self.statistics_path, self._empty_statistics())

    def _empty_statistics(self) -> Dict[str, Any]:
        return {
            "updated_at": None,
            "total_runs": 0,
            "total_good_runs": 0,
            "total_promoted": 0,
            "total_memory_count": 0,
        }

    def _load_json(self, path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        if not path.exists():
            return dict(default)

        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception:
            pass

        return dict(default)

    def _save_json(self, path: Path, data: Dict[str, Any]) -> None:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
