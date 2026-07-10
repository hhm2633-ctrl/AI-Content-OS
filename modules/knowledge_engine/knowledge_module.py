from datetime import datetime
from typing import Any, Dict, Optional

from modules.base_module import BaseModule
from modules.knowledge_engine.duplicate_detector import KnowledgeDuplicateDetector
from modules.knowledge_engine.knowledge_classifier import KnowledgeClassifier
from modules.knowledge_engine.knowledge_extractor import KnowledgeExtractor
from modules.knowledge_engine.knowledge_history import KnowledgeHistory
from modules.knowledge_engine.knowledge_index import KnowledgeIndex
from modules.knowledge_engine.knowledge_interface import KnowledgeInterface
from modules.knowledge_engine.knowledge_ranker import KnowledgeRanker
from modules.knowledge_engine.knowledge_score import KnowledgeScorer
from modules.knowledge_engine.knowledge_storage import KnowledgeStorage


class KnowledgeModule(BaseModule):
    """
    Knowledge Intelligence v1.

    WorkflowEngine의 각 Engine이 만든 결과(Pattern/Research/Content/ImageStrategy/
    CardNews/Publishing)에서 재사용 가능한 Knowledge(Hook/CTA/Pattern/Layout/Brand/
    Workflow/Prompt Pattern/Tool/Image Strategy/Funnel)를 추출 -> 분류 -> 중복 검사 ->
    점수화 -> 정렬한 뒤 storage/knowledge/에 누적 저장한다.

    Pattern Engine/Research/Content/Image Strategy/CardNews가 향후 이 Knowledge를
    조회할 수 있도록 KnowledgeInterface API를 준비하지만, 이번 Chapter에서는 다른
    Engine에서 실제로 호출하도록 연결하지 않는다 (API만 준비).

    WorkflowEngine은 PublishingModule 다음, 최종 결과 조립 이전에 이 모듈을 호출한다.
    이 모듈 자체가 실패해도 workflow_completed를 깨지 않도록, 실패 시 빈 Knowledge
    DB 존재를 보장하고 fallback_used=True인 안전한 결과를 반환한다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        try:
            super().__init__(config=config)
        except TypeError:
            super().__init__()

        self.config = config or getattr(self, "config", {}) or {}

        self.extractor = KnowledgeExtractor(self.config)
        self.classifier = KnowledgeClassifier(self.config)
        self.duplicate_detector = KnowledgeDuplicateDetector(self.config)
        self.scorer = KnowledgeScorer(self.config)
        self.ranker = KnowledgeRanker(self.config)

        self.storage = KnowledgeStorage()
        self.history = KnowledgeHistory()
        self.index = KnowledgeIndex()

        # Interface는 다른 Engine이 향후 재사용할 수 있도록 준비만 해 둔다.
        self.interface = KnowledgeInterface(self.storage, self.index)

        try:
            self.storage.ensure_exists()
        except Exception as error:
            print(f"Knowledge Storage Init Ensure Failed: {error}")

    def run(
        self,
        pattern_result: Optional[Dict[str, Any]] = None,
        research_result: Optional[Dict[str, Any]] = None,
        content_result: Optional[Dict[str, Any]] = None,
        image_strategy_result: Optional[Dict[str, Any]] = None,
        card_news_result: Optional[Dict[str, Any]] = None,
        publishing_result: Optional[Dict[str, Any]] = None,
        trend_result: Optional[Dict[str, Any]] = None,
        topic_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        print("Knowledge Module Started")

        context = {
            "trend_result": trend_result or {},
            "topic_result": topic_result or {},
            "pattern_result": pattern_result or {},
            "research_result": research_result or {},
            "content_result": content_result or {},
            "image_strategy_result": image_strategy_result or {},
            "card_news_result": card_news_result or {},
            "publishing_result": publishing_result or {},
        }

        try:
            result = self._build_result(context)
        except Exception as error:
            print(f"Knowledge Module Failed, safe fallback returned: {error}")
            result = self._fallback_result(reason=f"knowledge_module_exception: {error}")

        print("Knowledge Module Finished")
        return result

    def _build_result(self, context: Dict[str, Any]) -> Dict[str, Any]:
        extracted_items = self.extractor.extract(context)
        classified_items = self.classifier.classify(extracted_items, context)
        checked_items = self.duplicate_detector.check(classified_items)
        scored_items = self.scorer.score(checked_items, context)
        ranked_items = self.ranker.rank(scored_items)

        upsert_summary = self.storage.upsert(ranked_items)

        # Knowledge Rank 고도화: 이번 실행분만이 아니라 누적 DB 전체를 다시 정렬해
        # 모든 레코드의 rank가 항상 전체 DB 기준 최신 순위를 반영하도록 한다.
        all_records = self.storage.load_all()
        globally_ranked_records = self.ranker.rank(all_records)
        self.storage.replace_all(globally_ranked_records)

        self.index.rebuild(globally_ranked_records)

        run_fallback_used = any(bool(item.get("fallback_used")) for item in ranked_items)

        statistics = self.storage.update_statistics(ranked_items, run_fallback_used)
        self.storage.update_score_statistics(globally_ranked_records)

        self.history.record(
            items=ranked_items,
            upsert_summary=upsert_summary,
            fallback_used=run_fallback_used,
            reason="" if ranked_items else "no_knowledge_extracted_this_run",
        )

        by_type_count: Dict[str, int] = {}
        for item in ranked_items:
            knowledge_type = str(item.get("type", "unknown"))
            by_type_count[knowledge_type] = by_type_count.get(knowledge_type, 0) + 1

        top_knowledge = [
            {
                "knowledge_id": item.get("knowledge_id"),
                "type": item.get("type"),
                "title": item.get("title"),
                "overall_score": (item.get("score") or {}).get("overall_score", 0.0),
            }
            for item in ranked_items[:5]
        ]

        return {
            "status": "knowledge_extracted",
            "extracted_count": len(ranked_items),
            "new_count": upsert_summary.get("new_count", 0),
            "updated_count": upsert_summary.get("updated_count", 0),
            "total_knowledge_count": upsert_summary.get("total_count", 0),
            "by_type": by_type_count,
            "top_knowledge": top_knowledge,
            "statistics": statistics,
            "fallback_used": run_fallback_used,
            "reason": "",
            "created_at": datetime.now().isoformat(),
        }

    def _fallback_result(self, reason: str) -> Dict[str, Any]:
        statistics: Dict[str, Any] = {}

        try:
            self.storage.ensure_exists()
            statistics = self.storage.update_statistics([], fallback_used=True)
        except Exception as error:
            print(f"Knowledge Fallback DB Ensure Failed: {error}")

        try:
            self.history.record(items=[], upsert_summary={}, fallback_used=True, reason=reason)
        except Exception as error:
            print(f"Knowledge Fallback History Write Failed: {error}")

        return {
            "status": "knowledge_extracted",
            "extracted_count": 0,
            "new_count": 0,
            "updated_count": 0,
            "total_knowledge_count": statistics.get("total_knowledge_count", 0),
            "by_type": {},
            "top_knowledge": [],
            "statistics": statistics,
            "fallback_used": True,
            "reason": reason,
            "created_at": datetime.now().isoformat(),
        }
