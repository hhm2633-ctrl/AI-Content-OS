import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class KnowledgeStorage(object):
    """
    Knowledge Engine - Storage.

    storage/knowledge/knowledge.json (누적 Knowledge DB, knowledge_id 기준 upsert)와
    storage/knowledge/knowledge_statistics.json (누적 통계)을 관리한다.

    파일이 없거나 손상되어 있어도 빈 DB/기본 통계로 취급하고, 쓰기 실패는 예외를
    던지지 않고 로그만 남긴다. Knowledge 저장 실패가 workflow_completed를 깨서는
    안 된다는 Fallback-first 계약을 그대로 따른다.

    Knowledge Cache: 같은 실행(run) 안에서 여러 Engine이 반복적으로 load_all()을
    호출해도 디스크를 매번 다시 읽지 않도록 간단한 인스턴스 캐시를 둔다. upsert/
    replace_all로 기록하면 캐시가 즉시 최신 상태로 갱신된다(수동 무효화 불필요).
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("storage/knowledge")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.knowledge_path = self.output_dir / "knowledge.json"
        self.statistics_path = self.output_dir / "knowledge_statistics.json"

        self._cache: Optional[List[Dict[str, Any]]] = None

    def ensure_exists(self) -> None:
        try:
            if not self.knowledge_path.exists():
                self._save_json(self.knowledge_path, self._empty_knowledge_db())

            if not self.statistics_path.exists():
                self._save_json(self.statistics_path, self._empty_statistics())
        except Exception as error:
            print(f"Knowledge Storage Ensure Exists Failed: {error}")

    def load_all(self) -> List[Dict[str, Any]]:
        if self._cache is not None:
            return self._cache

        data = self._load_json(self.knowledge_path, self._empty_knowledge_db())
        records = data.get("records", [])
        records = records if isinstance(records, list) else []

        self._cache = records
        return records

    def replace_all(self, records: List[Dict[str, Any]]) -> None:
        """Knowledge Rank 재계산 등으로 전체 레코드 순서/필드가 바뀐 경우 통째로 덮어쓴다."""
        records = records if isinstance(records, list) else []

        self._save_json(
            self.knowledge_path,
            {
                "updated_at": datetime.now().isoformat(),
                "total_count": len(records),
                "records": records,
            },
        )

        self._cache = records

    def upsert(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        existing = self.load_all()
        existing_by_id = {
            record.get("knowledge_id"): record
            for record in existing
            if isinstance(record, dict) and record.get("knowledge_id")
        }

        new_count = 0
        updated_count = 0

        for item in items or []:
            if not isinstance(item, dict):
                continue

            knowledge_id = item.get("knowledge_id")

            if not knowledge_id:
                continue

            if knowledge_id in existing_by_id:
                updated_count += 1
            else:
                new_count += 1

            existing_by_id[knowledge_id] = item

        merged_records = list(existing_by_id.values())

        self._save_json(
            self.knowledge_path,
            {
                "updated_at": datetime.now().isoformat(),
                "total_count": len(merged_records),
                "records": merged_records,
            },
        )

        self._cache = merged_records

        return {
            "total_count": len(merged_records),
            "new_count": new_count,
            "updated_count": updated_count,
        }

    def update_statistics(self, items: List[Dict[str, Any]], fallback_used: bool) -> Dict[str, Any]:
        statistics = self._load_json(self.statistics_path, self._empty_statistics())

        statistics["total_runs"] = int(statistics.get("total_runs", 0)) + 1

        if fallback_used:
            statistics["total_fallback_runs"] = int(statistics.get("total_fallback_runs", 0)) + 1

        by_type = statistics.get("by_type", {})
        if not isinstance(by_type, dict):
            by_type = {}

        for item in items or []:
            if not isinstance(item, dict):
                continue

            knowledge_type = str(item.get("type", "unknown"))
            by_type[knowledge_type] = int(by_type.get(knowledge_type, 0)) + 1

        statistics["by_type"] = by_type
        statistics["total_knowledge_count"] = len(self.load_all())
        statistics["updated_at"] = datetime.now().isoformat()

        self._save_json(self.statistics_path, statistics)
        return statistics

    def load_statistics(self) -> Dict[str, Any]:
        return self._load_json(self.statistics_path, self._empty_statistics())

    def update_score_statistics(self, all_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Knowledge DB 고도화: 전체 레코드 기준 type별 평균 overall_score를 통계에 반영한다."""
        statistics = self._load_json(self.statistics_path, self._empty_statistics())

        totals: Dict[str, float] = {}
        counts: Dict[str, int] = {}

        for record in all_records or []:
            if not isinstance(record, dict):
                continue

            knowledge_type = str(record.get("type", "unknown"))
            overall_score = (record.get("score") or {}).get("overall_score")

            if not isinstance(overall_score, (int, float)):
                continue

            totals[knowledge_type] = totals.get(knowledge_type, 0.0) + float(overall_score)
            counts[knowledge_type] = counts.get(knowledge_type, 0) + 1

        average_by_type = {
            knowledge_type: round(totals[knowledge_type] / counts[knowledge_type], 4)
            for knowledge_type in totals
            if counts.get(knowledge_type)
        }

        statistics["average_overall_score_by_type"] = average_by_type
        statistics["updated_at"] = datetime.now().isoformat()

        self._save_json(self.statistics_path, statistics)
        return statistics

    def _empty_knowledge_db(self) -> Dict[str, Any]:
        return {
            "updated_at": None,
            "total_count": 0,
            "records": [],
        }

    def _empty_statistics(self) -> Dict[str, Any]:
        return {
            "updated_at": None,
            "total_runs": 0,
            "total_fallback_runs": 0,
            "total_knowledge_count": 0,
            "by_type": {},
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
