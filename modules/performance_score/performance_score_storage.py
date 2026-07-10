import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class PerformanceScoreStorage(object):
    """
    Performance Score - Storage.

    storage/performance_score/performance_score.json (최신 점수)와
    storage/performance_score/performance_score_statistics.json (누적 평균/통계)을 관리한다.
    파일이 없거나 손상되어도 안전한 기본값으로 취급한다.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("storage/performance_score")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.result_path = self.output_dir / "performance_score.json"
        self.statistics_path = self.output_dir / "performance_score_statistics.json"

    def save(self, result: Dict[str, Any]) -> None:
        try:
            self._save_json(self.result_path, result)
        except Exception as error:
            print(f"Performance Score Save Failed: {error}")

    def load_latest(self) -> Dict[str, Any]:
        return self._load_json(self.result_path, {})

    def update_statistics(self, scores: Dict[str, Any]) -> Dict[str, Any]:
        statistics = self._load_json(self.statistics_path, self._empty_statistics())

        statistics["total_runs"] = int(statistics.get("total_runs", 0)) + 1

        for field in ("hook_score", "cta_score", "layout_score", "brand_score", "image_score", "overall_performance_score"):
            value = scores.get(field)

            if not isinstance(value, (int, float)):
                continue

            running_average = statistics.get("average", {})
            if not isinstance(running_average, dict):
                running_average = {}

            previous_average = float(running_average.get(field, value))
            previous_runs = max(1, int(statistics.get("total_runs", 1)) - 1)

            new_average = ((previous_average * previous_runs) + float(value)) / (previous_runs + 1)
            running_average[field] = round(new_average, 4)
            statistics["average"] = running_average

        statistics["updated_at"] = datetime.now().isoformat()

        self._save_json(self.statistics_path, statistics)
        return statistics

    def load_statistics(self) -> Dict[str, Any]:
        return self._load_json(self.statistics_path, self._empty_statistics())

    def _empty_statistics(self) -> Dict[str, Any]:
        return {
            "updated_at": None,
            "total_runs": 0,
            "average": {},
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
