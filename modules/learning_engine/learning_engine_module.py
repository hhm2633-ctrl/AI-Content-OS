from datetime import datetime
from typing import Any, Dict, List, Optional

from modules.base_module import BaseModule
from modules.learning_engine.learning_history import LearningHistory
from modules.learning_engine.learning_interface import LearningInterface
from modules.learning_engine.learning_score import LearningScorer
from modules.learning_engine.learning_selector import LearningSelector
from modules.learning_engine.learning_storage import LearningStorage


class LearningEngineModule(BaseModule):
    """
    Learning Engine v2 (Sprint 13).

    실제 SNS 성과 데이터(조회수/저장수 등)는 없으므로 가짜 성과를 만들지 않는다.
    대신 이미 로컬에서 실제로 계산된 audit_score + performance_score +
    knowledge_score(이번 실행에서 Knowledge Engine이 추출한 top_knowledge의
    overall_score 평균)를 합쳐 `internal_learning_score`를 만든다.

    `internal_learning_score`가 기준(0.65) 이상인 "좋은 실행"에서 나온 고성과
    Hook/CTA/Pattern/Layout/Brand Knowledge만 골라
    storage/learning/learning_memory.json에 승격(promote)한다. 같은 항목이 여러 번
    좋은 실행에서 반복되면 memory_score가 점점 올라간다(reinforcement).

    Knowledge DB를 실제로 읽어 knowledge_score/승격 후보를 만들므로
    `knowledge_used`/`knowledge_items`/`knowledge_influence` 필드로 사용 흔적을
    남긴다.

    이 Engine은 외부 네트워크/LLM을 호출하지 않으며, 계산 실패 시 승격 없이 안전한
    기본 결과를 반환한다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}

        self.selector = LearningSelector(self.config)
        self.scorer = LearningScorer(self.config)
        self.storage = LearningStorage()
        self.history = LearningHistory()
        self.interface = LearningInterface(self.storage)

    def run(
        self,
        knowledge_result: Optional[Dict[str, Any]] = None,
        performance_score_result: Optional[Dict[str, Any]] = None,
        audit_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        print("Learning Engine Module Started")

        try:
            result = self._build_result(
                knowledge_result or {}, performance_score_result or {}, audit_result or {}
            )
        except Exception as error:
            print(f"Learning Engine Module Failed, safe fallback returned: {error}")
            result = self._fallback_result(reason=f"learning_engine_exception: {error}")

        print("Learning Engine Module Finished")
        return result

    def _build_result(
        self,
        knowledge_result: Dict[str, Any],
        performance_score_result: Dict[str, Any],
        audit_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        top_knowledge = knowledge_result.get("top_knowledge", [])
        if not isinstance(top_knowledge, list):
            top_knowledge = []

        selection = self.selector.select(top_knowledge, performance_score_result, audit_result)
        candidates: List[Dict[str, Any]] = selection.get("candidates", [])

        existing_memory = {
            record.get("knowledge_id"): record
            for record in self.storage.load_memory()
            if isinstance(record, dict) and record.get("knowledge_id")
        }

        promoted_entries = []

        for candidate in candidates:
            knowledge_id = candidate.get("knowledge_id")
            existing_entry = existing_memory.get(knowledge_id)

            score_result = self.scorer.compute(existing_entry, float(candidate.get("overall_score", 0.0)))

            promoted_entries.append({
                "knowledge_id": knowledge_id,
                "type": candidate.get("type"),
                "title": candidate.get("title"),
                "memory_score": score_result.get("memory_score", 0.0),
                "reinforced_count": score_result.get("reinforced_count", 1),
                "promoted_at": datetime.now().isoformat(),
            })

        if promoted_entries:
            self.storage.upsert_memory(promoted_entries)

        statistics = self.storage.update_statistics(
            is_good_run=bool(selection.get("is_good_run", False)),
            promoted_count=len(promoted_entries),
        )

        self.history.record(
            internal_learning_score=selection.get("internal_learning_score", 0.0),
            is_good_run=bool(selection.get("is_good_run", False)),
            promoted_count=len(promoted_entries),
        )

        knowledge_items = [
            {"knowledge_id": item.get("knowledge_id"), "type": item.get("type"), "title": item.get("title")}
            for item in top_knowledge
        ]

        return {
            "status": "learning_completed",
            "internal_learning_score": selection.get("internal_learning_score", 0.0),
            "audit_score": selection.get("audit_score", 0.0),
            "performance_score": selection.get("performance_score", 0.0),
            "knowledge_score": selection.get("knowledge_score", 0.0),
            "is_good_run": selection.get("is_good_run", False),
            "promoted_count": len(promoted_entries),
            "promoted_entries": promoted_entries,
            "total_memory_count": statistics.get("total_memory_count", 0),
            "knowledge_used": selection.get("knowledge_used", bool(knowledge_items)),
            "knowledge_items": knowledge_items,
            "knowledge_influence": (
                f"knowledge_score={selection.get('knowledge_score', 0.0)}를 internal_learning_score 계산에 "
                f"반영함(가중치 {LearningSelector.KNOWLEDGE_WEIGHT}). {len(promoted_entries)}건을 "
                "learning_memory에 승격함." if knowledge_items else
                "이번 실행에서 참고할 Knowledge 항목이 없어 knowledge_score는 기본값(0.5)을 사용함."
            ),
            "reason": selection.get("reason", ""),
            "fallback_used": False,
            "created_at": datetime.now().isoformat(),
        }

    def _fallback_result(self, reason: str) -> Dict[str, Any]:
        try:
            statistics = self.storage.load_statistics()
        except Exception:
            statistics = {}

        return {
            "status": "learning_completed",
            "internal_learning_score": 0.0,
            "audit_score": 0.0,
            "performance_score": 0.0,
            "knowledge_score": 0.0,
            "is_good_run": False,
            "promoted_count": 0,
            "promoted_entries": [],
            "total_memory_count": statistics.get("total_memory_count", 0) if isinstance(statistics, dict) else 0,
            "knowledge_used": False,
            "knowledge_items": [],
            "knowledge_influence": "",
            "reason": reason,
            "fallback_used": True,
            "created_at": datetime.now().isoformat(),
        }
