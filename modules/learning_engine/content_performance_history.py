import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ContentPerformanceHistory(object):
    """
    Learning Engine 확장 (Instagram Intelligence Phase 2) - Content Performance
    History.

    storage/history/content_performance_history.json에 이번 실행에서 실제로
    만들어진 콘텐츠의 hook/cta/pattern/layout/brand_dna_snapshot/quality_score/
    competitor_reference/knowledge_reference를 append-only로 누적한다. 이미
    다른 Engine이 계산해 둔 값만 그대로 옮겨 적으며, 이 클래스 자체는 아무 값도
    새로 계산하지 않는다(없는 값은 그대로 없는 채로 기록한다).

    파일이 없거나 손상돼도 예외를 던지지 않고 빈 이력으로 취급한다.
    """

    MAX_RECORDS = 500

    def __init__(self, history_path: Optional[Path] = None):
        self.history_path = history_path or Path("storage/history/content_performance_history.json")
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

    def build_content_id(self, title: str, secondary_key: str) -> str:
        """
        content_id는 새 신호를 만들어내는 것이 아니라, 이미 존재하는 콘텐츠
        자체의 값(title/caption 등)으로부터 안정적인 식별자를 구성하는
        것뿐이다 - Knowledge Engine의 `knowledge_id` 구성 방식(실제 값을
        조합해 id를 만듦)과 같은 원칙이다.

        의도적으로 기록 시각(`datetime.now()`)은 절대 넣지 않는다 - 넣으면
        같은 콘텐츠를 다시 처리해도 매번 다른 id가 나와 중복 방지가 아예
        작동하지 않게 된다. title/caption처럼 콘텐츠 자체에서 나온, 같은
        콘텐츠라면 항상 같은 값을 조합해야 한다.
        """
        raw = f"{title or ''}|{secondary_key or ''}".encode("utf-8", errors="ignore")
        return hashlib.sha1(raw).hexdigest()[:16]

    def record(self, entry: Dict[str, Any]) -> None:
        try:
            self._record(entry or {})
        except Exception as error:
            print(f"Content Performance History Write Failed: {error}")

    def record_once(self, entry: Dict[str, Any]) -> bool:
        """
        위험 A 방지: 같은 content_id가 이미 기록에 있으면 다시 추가하지 않고
        `False`를 반환한다(중복 누적 방지). 새 content_id면 그대로 기록하고
        `True`를 반환한다. content_id가 비어 있으면(구성 실패) 안전하게
        기록하지 않는다 - 빈 id로 잘못 dedup되는 것을 막기 위함이다.
        """
        try:
            content_id = (entry or {}).get("content_id")

            if not content_id:
                print("Content Performance History Skipped: empty content_id")
                return False

            existing_ids = {
                record.get("content_id")
                for record in self.load_all()
                if isinstance(record, dict)
            }

            if content_id in existing_ids:
                return False

            self._record(entry)
            return True
        except Exception as error:
            print(f"Content Performance History Write Failed: {error}")
            return False

    def _record(self, entry: Dict[str, Any]) -> None:
        history = self._load_json()
        records = history.get("records", [])

        if not isinstance(records, list):
            records = []

        records.append(entry)

        if len(records) > self.MAX_RECORDS:
            records = records[-self.MAX_RECORDS:]

        self._save_json({"updated_at": datetime.now().isoformat(), "records": records})

    def load_all(self) -> List[Dict[str, Any]]:
        history = self._load_json()
        records = history.get("records", [])
        return records if isinstance(records, list) else []

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
