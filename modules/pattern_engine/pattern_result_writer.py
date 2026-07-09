import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class PatternResultWriter:
    """
    Pattern Engine 결과를 storage/pattern/에 기록한다.

    - pattern_result.json: 최신 실행 결과
    - pattern_history.json: 실행 이력 (append-only)
    - pattern_statistics.json: pattern/hook/cta/layout 선택 누적 통계
    """

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("storage/pattern")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.result_path = self.output_dir / "pattern_result.json"
        self.history_path = self.output_dir / "pattern_history.json"
        self.statistics_path = self.output_dir / "pattern_statistics.json"

    def write(self, result: Dict[str, Any]) -> Dict[str, Any]:
        result = result if isinstance(result, dict) else {}

        self._save_json(self.result_path, result)

        try:
            self._append_history(result)
        except Exception as error:
            print(f"Pattern History Write Failed: {error}")

        try:
            self._update_statistics(result)
        except Exception as error:
            print(f"Pattern Statistics Write Failed: {error}")

        return {
            "pattern_result_path": str(self.result_path).replace("\\", "/"),
            "pattern_history_path": str(self.history_path).replace("\\", "/"),
            "pattern_statistics_path": str(self.statistics_path).replace("\\", "/"),
        }

    def _append_history(self, result: Dict[str, Any]) -> None:
        history = self._load_json(self.history_path, {"updated_at": None, "records": []})
        records = history.get("records", [])

        if not isinstance(records, list):
            records = []

        topic_intelligence = result.get("topic_intelligence") or {}
        pattern_plan = result.get("pattern_plan") or {}
        selected_topic = result.get("selected_topic") or {}

        records.append(
            {
                "recorded_at": datetime.now().isoformat(),
                "status": result.get("status", "unknown"),
                "selected_topic_title": selected_topic.get("title", ""),
                "category": topic_intelligence.get("category", ""),
                "cluster": topic_intelligence.get("cluster", ""),
                "confidence_score": topic_intelligence.get("confidence_score", 0.0),
                "pattern_type": pattern_plan.get("pattern_type", ""),
                "hook_type": pattern_plan.get("hook_type", ""),
                "cta_type": pattern_plan.get("cta_type", ""),
                "layout_type": pattern_plan.get("layout_type", ""),
                "fallback_used": bool(result.get("fallback_used", False)),
            }
        )

        self._save_json(
            self.history_path,
            {
                "updated_at": datetime.now().isoformat(),
                "records": records,
            },
        )

    def _update_statistics(self, result: Dict[str, Any]) -> None:
        statistics = self._load_json(
            self.statistics_path,
            {
                "updated_at": None,
                "total_runs": 0,
                "total_fallback_used": 0,
                "pattern_type": {},
                "hook_type": {},
                "cta_type": {},
                "layout_type": {},
            },
        )

        pattern_plan = result.get("pattern_plan") or {}

        statistics["total_runs"] = int(statistics.get("total_runs", 0)) + 1

        if result.get("fallback_used"):
            statistics["total_fallback_used"] = int(statistics.get("total_fallback_used", 0)) + 1

        for field in ("pattern_type", "hook_type", "cta_type", "layout_type"):
            value = str(pattern_plan.get(field, "unknown"))
            bucket = statistics.get(field, {})

            if not isinstance(bucket, dict):
                bucket = {}

            bucket[value] = int(bucket.get(value, 0)) + 1
            statistics[field] = bucket

        statistics["updated_at"] = datetime.now().isoformat()

        self._save_json(self.statistics_path, statistics)

    def _load_json(self, path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        if not path.exists():
            return default

        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception:
            pass

        return default

    def _save_json(self, path: Path, data: Dict[str, Any]) -> None:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
