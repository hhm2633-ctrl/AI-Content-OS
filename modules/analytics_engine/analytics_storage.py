import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class AnalyticsStorage(object):
    """
    Analytics Engine - Storage (Sprint 13: 실측 데이터만 저장).

    storage/analytics/analytics_result.json (최신 내부 품질 추세)과
    storage/analytics/analytics_statistics.json (추세 판정 누적 통계)을 관리한다.
    허구의 조회수/저장수 등은 저장하지 않는다 - 전부 로컬에서 실제로 계산된
    Performance/Audit Score 비교 결과만 저장한다.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("storage/analytics")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.result_path = self.output_dir / "analytics_result.json"
        self.statistics_path = self.output_dir / "analytics_statistics.json"

    def save(self, result: Dict[str, Any]) -> None:
        try:
            self._save_json(self.result_path, result)
        except Exception as error:
            print(f"Analytics Storage Save Failed: {error}")

    def load_latest(self) -> Dict[str, Any]:
        return self._load_json(self.result_path, {})

    def update_statistics(self, quality_trend: str) -> Dict[str, Any]:
        statistics = self._load_json(self.statistics_path, self._empty_statistics())
        statistics["total_runs"] = int(statistics.get("total_runs", 0)) + 1

        trend_counts = statistics.get("trend_counts", {})
        if not isinstance(trend_counts, dict):
            trend_counts = {}

        trend_counts[quality_trend] = int(trend_counts.get(quality_trend, 0)) + 1
        statistics["trend_counts"] = trend_counts
        statistics["updated_at"] = datetime.now().isoformat()

        self._save_json(self.statistics_path, statistics)
        return statistics

    def load_statistics(self) -> Dict[str, Any]:
        return self._load_json(self.statistics_path, self._empty_statistics())

    def _empty_statistics(self) -> Dict[str, Any]:
        return {
            "updated_at": None,
            "total_runs": 0,
            "trend_counts": {},
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
