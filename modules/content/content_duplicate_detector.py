import json
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ContentDuplicateDetector:
    """
    최근 생성 콘텐츠(storage/content/content_history.json)와 제목/Hook/CTA 문구를
    비교해 duplicate_risk(low/medium/high)를 판정한다.

    파일이 없거나 손상되어도 예외를 던지지 않고 빈 이력으로 취급하며,
    비교/기록에 실패해도 workflow에 영향을 주지 않는다.
    """

    HIGH_SIMILARITY_THRESHOLD = 0.9
    MEDIUM_SIMILARITY_THRESHOLD = 0.6
    MAX_HISTORY_CHECK = 30
    MAX_HISTORY_RECORDS = 500

    def __init__(self, config: Optional[Dict[str, Any]] = None, history_path: Optional[Path] = None):
        self.config = config or {}
        self.history_path = history_path or Path("storage/content/content_history.json")

    def check(self, content_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            return self._check(content_result or {})
        except Exception:
            return {
                "duplicate_risk": "low",
                "similarity_score": 0.0,
                "matched_title": "",
                "reason": "중복 검사 실패로 안전하게 low 처리함.",
            }

    def record(self, content_result: Optional[Dict[str, Any]]) -> None:
        try:
            self._record(content_result or {})
        except Exception as error:
            print(f"Content History Write Failed: {error}")

    def _check(self, content_result: Dict[str, Any]) -> Dict[str, Any]:
        history = self._load_history()
        records = history.get("records", [])

        if not isinstance(records, list):
            records = []

        recent_records = records[-self.MAX_HISTORY_CHECK:]

        current_title = str(content_result.get("title", "")).strip()
        current_hook, current_cta = self._extract_hook_cta_text(content_result)

        best_similarity = 0.0
        best_match_title = ""

        for record in recent_records:
            if not isinstance(record, dict):
                continue

            title_similarity = self._similarity(current_title, str(record.get("title", "")))
            hook_similarity = self._similarity(current_hook, str(record.get("hook_text", "")))
            cta_similarity = self._similarity(current_cta, str(record.get("cta_text", "")))

            combined = max(
                title_similarity,
                (title_similarity * 0.5) + (hook_similarity * 0.25) + (cta_similarity * 0.25),
            )

            if combined > best_similarity:
                best_similarity = combined
                best_match_title = str(record.get("title", ""))

        if best_similarity >= self.HIGH_SIMILARITY_THRESHOLD:
            duplicate_risk = "high"
        elif best_similarity >= self.MEDIUM_SIMILARITY_THRESHOLD:
            duplicate_risk = "medium"
        else:
            duplicate_risk = "low"

        return {
            "duplicate_risk": duplicate_risk,
            "similarity_score": round(best_similarity, 4),
            "matched_title": best_match_title,
            "checked_against": len(recent_records),
            "reason": (
                f"최근 {len(recent_records)}건과 비교해 최대 유사도 "
                f"{round(best_similarity, 4)}로 '{duplicate_risk}' 판정."
            ),
        }

    def _record(self, content_result: Dict[str, Any]) -> None:
        history = self._load_history()
        records = history.get("records", [])

        if not isinstance(records, list):
            records = []

        hook_text, cta_text = self._extract_hook_cta_text(content_result)

        records.append(
            {
                "recorded_at": datetime.now().isoformat(),
                "title": str(content_result.get("title", "")),
                "hook_text": hook_text,
                "cta_text": cta_text,
                "caption": str(content_result.get("caption", "")),
                "hashtags": content_result.get("hashtags", []),
                "fallback_used": bool(content_result.get("fallback_used", False)),
            }
        )

        if len(records) > self.MAX_HISTORY_RECORDS:
            records = records[-self.MAX_HISTORY_RECORDS:]

        self._save_history(
            {
                "updated_at": datetime.now().isoformat(),
                "records": records,
            }
        )

    def _extract_hook_cta_text(self, content_result: Dict[str, Any]) -> Tuple[str, str]:
        slides = content_result.get("slides", [])
        hook_text = ""
        cta_text = ""

        if isinstance(slides, list):
            for slide in slides:
                if not isinstance(slide, dict):
                    continue

                role = slide.get("role")

                if role == "hook" and not hook_text:
                    hook_text = f"{slide.get('headline', '')} {slide.get('body', '')}".strip()

                if role == "cta" and not cta_text:
                    cta_text = f"{slide.get('headline', '')} {slide.get('body', '')}".strip()

        return hook_text, cta_text

    def _similarity(self, text_a: str, text_b: str) -> float:
        text_a = str(text_a or "").strip().lower()
        text_b = str(text_b or "").strip().lower()

        if not text_a or not text_b:
            return 0.0

        return SequenceMatcher(None, text_a, text_b).ratio()

    def _load_history(self) -> Dict[str, Any]:
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

    def _save_history(self, data: Dict[str, Any]) -> None:
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.history_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
