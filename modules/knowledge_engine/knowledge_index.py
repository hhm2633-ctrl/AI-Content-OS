import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class KnowledgeIndex(object):
    """
    Knowledge Engine - Index.

    storage/knowledge/knowledge_index.json에 type별/tag별 knowledge_id 색인을
    유지한다. KnowledgeInterface가 knowledge.json 전체를 매번 스캔하지 않고 빠르게
    조회할 수 있도록 돕는 보조 구조이며, 손상되어도 knowledge.json 전체로부터
    다시 rebuild() 할 수 있다 (색인 손실이 knowledge 데이터 손실로 이어지지 않음).
    """

    def __init__(self, index_path: Optional[Path] = None):
        self.index_path = index_path or Path("storage/knowledge/knowledge_index.json")
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

    def rebuild(self, all_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        by_type: Dict[str, List[str]] = {}
        by_tag: Dict[str, List[str]] = {}

        for record in all_records or []:
            if not isinstance(record, dict):
                continue

            knowledge_id = record.get("knowledge_id")

            if not knowledge_id:
                continue

            knowledge_type = str(record.get("type", "unknown"))
            by_type.setdefault(knowledge_type, []).append(knowledge_id)

            tags = record.get("tags", [])
            if isinstance(tags, list):
                for tag in tags:
                    tag = str(tag)
                    if tag:
                        by_tag.setdefault(tag, []).append(knowledge_id)

        index = {
            "updated_at": datetime.now().isoformat(),
            "total_indexed": len(all_records or []),
            "by_type": by_type,
            "by_tag": by_tag,
        }

        try:
            self._save_json(index)
        except Exception as error:
            print(f"Knowledge Index Write Failed: {error}")

        return index

    def load(self) -> Dict[str, Any]:
        if not self.index_path.exists():
            return self._empty_index()

        try:
            with open(self.index_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception:
            pass

        return self._empty_index()

    def _empty_index(self) -> Dict[str, Any]:
        return {
            "updated_at": None,
            "total_indexed": 0,
            "by_type": {},
            "by_tag": {},
        }

    def _save_json(self, data: Dict[str, Any]) -> None:
        with open(self.index_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
