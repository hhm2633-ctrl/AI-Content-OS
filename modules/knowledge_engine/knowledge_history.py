import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class KnowledgeHistory(object):
    """
    Knowledge Engine - History.

    Knowledge Engine 실행 이력을 storage/knowledge/knowledge_history.json에
    append-only로 기록한다 (pattern_history.json / content_history.json과
    동일한 규칙: 최근 MAX_RECORDS건만 유지, 기록 실패는 로그만 남기고 무시).
    """

    MAX_RECORDS = 500

    def __init__(self, history_path: Optional[Path] = None):
        self.history_path = history_path or Path("storage/knowledge/knowledge_history.json")
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        items: List[Dict[str, Any]],
        upsert_summary: Dict[str, Any],
        fallback_used: bool,
        reason: str = "",
    ) -> None:
        try:
            self._record(items or [], upsert_summary or {}, fallback_used, reason)
        except Exception as error:
            print(f"Knowledge History Write Failed: {error}")

    def _record(
        self,
        items: List[Dict[str, Any]],
        upsert_summary: Dict[str, Any],
        fallback_used: bool,
        reason: str,
    ) -> None:
        history = self._load_json()
        records = history.get("records", [])

        if not isinstance(records, list):
            records = []

        by_type: Dict[str, int] = {}
        for item in items:
            if not isinstance(item, dict):
                continue

            knowledge_type = str(item.get("type", "unknown"))
            by_type[knowledge_type] = by_type.get(knowledge_type, 0) + 1

        records.append(
            {
                "recorded_at": datetime.now().isoformat(),
                "extracted_count": len(items),
                "new_count": upsert_summary.get("new_count", 0),
                "updated_count": upsert_summary.get("updated_count", 0),
                "total_count": upsert_summary.get("total_count", 0),
                "by_type": by_type,
                "fallback_used": bool(fallback_used),
                "reason": reason,
            }
        )

        if len(records) > self.MAX_RECORDS:
            records = records[-self.MAX_RECORDS:]

        self._save_json(
            {
                "updated_at": datetime.now().isoformat(),
                "records": records,
            }
        )

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
