import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class AuditStorage(object):
    """
    Content Audit Engine - Storage.

    storage/audit/audit_result.json (최신 결과)과
    storage/audit/audit_statistics.json (누적 통계)을 관리한다.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("storage/audit")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.result_path = self.output_dir / "audit_result.json"
        self.statistics_path = self.output_dir / "audit_statistics.json"

    def save(self, result: Dict[str, Any]) -> None:
        try:
            self._save_json(self.result_path, result)
        except Exception as error:
            print(f"Audit Storage Save Failed: {error}")

    def load_latest(self) -> Dict[str, Any]:
        return self._load_json(self.result_path, {})

    def update_statistics(self, result: Dict[str, Any]) -> Dict[str, Any]:
        statistics = self._load_json(self.statistics_path, self._empty_statistics())

        statistics["total_runs"] = int(statistics.get("total_runs", 0)) + 1

        if result.get("passed"):
            statistics["total_passed"] = int(statistics.get("total_passed", 0)) + 1
        else:
            statistics["total_failed"] = int(statistics.get("total_failed", 0)) + 1

        for weakness in result.get("weaknesses", []) or []:
            weak_counts = statistics.get("weakness_counts", {})
            if not isinstance(weak_counts, dict):
                weak_counts = {}
            weak_counts[weakness] = int(weak_counts.get(weakness, 0)) + 1
            statistics["weakness_counts"] = weak_counts

        statistics["updated_at"] = datetime.now().isoformat()

        self._save_json(self.statistics_path, statistics)
        return statistics

    def load_statistics(self) -> Dict[str, Any]:
        return self._load_json(self.statistics_path, self._empty_statistics())

    def _empty_statistics(self) -> Dict[str, Any]:
        return {
            "updated_at": None,
            "total_runs": 0,
            "total_passed": 0,
            "total_failed": 0,
            "weakness_counts": {},
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
