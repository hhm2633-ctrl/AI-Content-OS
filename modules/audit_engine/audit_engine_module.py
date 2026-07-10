from datetime import datetime
from typing import Any, Dict, List, Optional

from modules.base_module import BaseModule
from modules.audit_engine.audit_checks import AuditChecks
from modules.audit_engine.audit_history import AuditHistory
from modules.audit_engine.audit_interface import AuditInterface
from modules.audit_engine.audit_score import AuditScorer
from modules.audit_engine.audit_storage import AuditStorage


class AuditEngineModule(BaseModule):
    """
    Content Audit Engine v2 (Sprint 13, docs/AUDIT_ENGINE.md "My Account Analysis").

    Hook/CTA/Pattern/Layout/Brand/Image Strategy/중복 위험/저장 유도/댓글 유도
    9개 항목을 검사해 하나의 audit_score와 강점/약점/추천 액션을 만든다.

    Sprint 13부터 content_result뿐 아니라 pattern_result(Pattern 일치 확인),
    knowledge_result(Knowledge DB 상위 항목의 duplicate_risk 반영),
    trend_memory_result(topic_repeat_risk 반영)를 실제로 읽어 검사에 반영한다
    (`knowledge_used`/`knowledge_items`/`knowledge_influence` 필드로 사용 흔적을
    남김). Competitor Comparison/Blind Spot Detection은 Competitor Engine 이력이
    축적된 뒤 별도 Sprint에서 추가한다.

    이 Engine은 외부 네트워크/LLM을 호출하지 않으며, 검사 실패 시 안전한 기본
    audit_score(0.0)와 수동 검수 권고를 반환한다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}

        self.checks = AuditChecks(self.config)
        self.scorer = AuditScorer(self.config)
        self.storage = AuditStorage()
        self.history = AuditHistory()
        self.interface = AuditInterface(self.storage)

    def run(
        self,
        content_result: Optional[Dict[str, Any]] = None,
        pattern_result: Optional[Dict[str, Any]] = None,
        card_news_result: Optional[Dict[str, Any]] = None,
        image_strategy_result: Optional[Dict[str, Any]] = None,
        performance_score_result: Optional[Dict[str, Any]] = None,
        knowledge_result: Optional[Dict[str, Any]] = None,
        trend_memory_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        print("Audit Engine Module Started")

        context = {
            "content_result": content_result or {},
            "pattern_result": pattern_result or {},
            "card_news_result": card_news_result or {},
            "image_strategy_result": image_strategy_result or {},
            "performance_score_result": performance_score_result or {},
            "knowledge_result": knowledge_result or {},
            "trend_memory_result": trend_memory_result or {},
        }

        try:
            result = self._build_result(context)
        except Exception as error:
            print(f"Audit Engine Module Failed, safe fallback returned: {error}")
            result = self._fallback_result(reason=f"audit_engine_exception: {error}")

        print("Audit Engine Module Finished")
        return result

    def _build_result(self, context: Dict[str, Any]) -> Dict[str, Any]:
        checks = self.checks.run_all(context)
        scored = self.scorer.score(checks)

        knowledge_usage = self._build_knowledge_usage(context["knowledge_result"])

        result = {
            "status": "audit_completed",
            "checks": checks,
            "audit_score": scored.get("audit_score", 0.0),
            "passed": scored.get("passed", False),
            "strengths": scored.get("strengths", []),
            "weaknesses": scored.get("weaknesses", []),
            "recommendations": scored.get("recommendations", []),
            "knowledge_used": knowledge_usage["knowledge_used"],
            "knowledge_items": knowledge_usage["knowledge_items"],
            "knowledge_influence": knowledge_usage["knowledge_influence"],
            "fallback_used": False,
            "created_at": datetime.now().isoformat(),
        }

        self.storage.save(result)
        self.storage.update_statistics(result)
        self.history.record(result)

        return result

    def _build_knowledge_usage(self, knowledge_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Knowledge DB 실제 소비(Sprint 13): duplicate_check가 이미 knowledge_result의
        top_knowledge를 읽어 판정에 반영했으므로, 여기서는 그 사용 흔적을
        knowledge_used/knowledge_items/knowledge_influence로 기록한다.
        """
        try:
            top_knowledge = knowledge_result.get("top_knowledge", [])
            if not isinstance(top_knowledge, list):
                top_knowledge = []

            knowledge_items = [
                {
                    "knowledge_id": item.get("knowledge_id"),
                    "type": item.get("type"),
                    "title": item.get("title"),
                    "duplicate_risk": item.get("duplicate_risk"),
                }
                for item in top_knowledge
            ]

            return {
                "knowledge_used": bool(knowledge_items),
                "knowledge_items": knowledge_items,
                "knowledge_influence": (
                    f"duplicate_check가 Knowledge DB 상위 {len(knowledge_items)}건의 duplicate_risk를 "
                    "함께 반영해 최종 중복 위험도를 판정함."
                    if knowledge_items
                    else "이번 실행에서 참고할 Knowledge 항목이 없어 duplicate_check는 content_intelligence만 사용함."
                ),
            }
        except Exception as error:
            print(f"Audit Knowledge Usage Failed: {error}")
            return {"knowledge_used": False, "knowledge_items": [], "knowledge_influence": f"실패: {error}"}

    def _fallback_result(self, reason: str) -> Dict[str, Any]:
        result = {
            "status": "audit_completed",
            "checks": {},
            "audit_score": 0.0,
            "passed": False,
            "strengths": [],
            "weaknesses": [],
            "recommendations": ["audit_engine 계산 실패 - 수동 검수 필요"],
            "knowledge_used": False,
            "knowledge_items": [],
            "knowledge_influence": "",
            "fallback_used": True,
            "reason": reason,
            "created_at": datetime.now().isoformat(),
        }

        try:
            self.storage.save(result)
            self.storage.update_statistics(result)
            self.history.record(result)
        except Exception as error:
            print(f"Audit Fallback Persist Failed: {error}")

        return result
