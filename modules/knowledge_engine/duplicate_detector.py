import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional


class KnowledgeDuplicateDetector(object):
    """
    Knowledge Engine - Duplicate Detector.

    새로 추출된 Knowledge 항목을 storage/knowledge/knowledge.json에 누적된
    같은 type의 기존 항목과 제목 유사도로 비교해 duplicate_risk(low/medium/high)를
    판정한다. content_duplicate_detector.py와 동일한 SequenceMatcher 기반 방식을
    사용한다.

    knowledge.json이 없거나 손상되어도 예외 없이 빈 DB로 취급하고, 개별 항목 비교가
    실패해도 해당 항목은 duplicate_risk=low로 안전하게 처리한다.
    """

    HIGH_SIMILARITY_THRESHOLD = 0.9
    MEDIUM_SIMILARITY_THRESHOLD = 0.6

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        knowledge_path: Optional[Path] = None,
    ):
        self.config = config or {}
        self.knowledge_path = knowledge_path or Path("storage/knowledge/knowledge.json")

    def check(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        existing = self._load_existing()
        checked = []

        for item in items or []:
            try:
                checked.append(self._check_item(item, existing))
            except Exception as error:
                print(f"Knowledge Duplicate Check Failed: {error}")
                safe_item = dict(item) if isinstance(item, dict) else {}
                safe_item["duplicate_risk"] = "low"
                safe_item["duplicate_similarity"] = 0.0
                safe_item["duplicate_matched_id"] = ""
                checked.append(safe_item)

        return checked

    def _check_item(
        self,
        item: Dict[str, Any],
        existing: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        item = dict(item)
        item_type = item.get("type", "")
        title = str(item.get("title", ""))

        best_similarity = 0.0
        best_id = ""

        for record in existing:
            if not isinstance(record, dict) or record.get("type") != item_type:
                continue

            if record.get("knowledge_id") and record.get("knowledge_id") == item.get("knowledge_id"):
                best_similarity = 1.0
                best_id = record.get("knowledge_id", "")
                break

            similarity = self._similarity(title, str(record.get("title", "")))

            if similarity > best_similarity:
                best_similarity = similarity
                best_id = record.get("knowledge_id", "")

        if best_similarity >= self.HIGH_SIMILARITY_THRESHOLD:
            duplicate_risk = "high"
        elif best_similarity >= self.MEDIUM_SIMILARITY_THRESHOLD:
            duplicate_risk = "medium"
        else:
            duplicate_risk = "low"

        item["duplicate_risk"] = duplicate_risk
        item["duplicate_similarity"] = round(best_similarity, 4)
        item["duplicate_matched_id"] = best_id

        return item

    def _similarity(self, text_a: str, text_b: str) -> float:
        text_a = str(text_a or "").strip().lower()
        text_b = str(text_b or "").strip().lower()

        if not text_a or not text_b:
            return 0.0

        return SequenceMatcher(None, text_a, text_b).ratio()

    def _load_existing(self) -> List[Dict[str, Any]]:
        if not self.knowledge_path.exists():
            return []

        try:
            with open(self.knowledge_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                records = data.get("records", [])

                if isinstance(records, list):
                    return records
        except Exception:
            pass

        return []
