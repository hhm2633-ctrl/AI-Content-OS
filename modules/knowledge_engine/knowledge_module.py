from datetime import datetime
from typing import Any, Dict, List, Optional

from modules.ai_planner.planner_consumer_adapter import PlannerConsumerAdapter, build_consumption_metadata
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

        # AI Planner Consumer Adapter 실제 연결(Sprint 15-3; Self Reference Guard
        # 수정 Sprint 16-0): KnowledgeRanker는 그대로 두고 실제 overall_score도
        # 전혀 건드리지 않는다. Sprint 15-3의 최초 구현은 planner_result.
        # knowledge_priority가 통과하면 이번 실행 항목의 overall_score를 실제로
        # +0.05 올린 뒤 그 값을 storage.upsert()로 영구 저장했는데, 이것이
        # average_overall_score_by_type(Historical Input)에 스며들어 다음 실행의
        # Planner가 "자신이 과거에 추천했다는 이유만으로 부풀려진 점수"를 실제
        # 성과처럼 다시 읽는 Circular Feedback을 만들었다(Sprint 16-0 Feedback
        # Audit에서 발견). 이제는 실제 score를 절대 바꾸지 않고, "Planner가
        # 우선순위로 지정한 타입이 실제 상위 항목과 얼마나 일치하는지"만 별도의
        # 진단 전용 필드(`planner_priority_preview`)로 보여준다 - `top_knowledge`
        # (Learning/Audit이 실제로 소비하는 필드)와 storage에 저장되는 값은 전혀
        # 영향받지 않는다.
        self.planner_consumer_adapter = PlannerConsumerAdapter()

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
        planner_result: Optional[Dict[str, Any]] = None,
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
            result = self._build_result(context, planner_result)
        except Exception as error:
            print(f"Knowledge Module Failed, safe fallback returned: {error}")
            result = self._fallback_result(reason=f"knowledge_module_exception: {error}")

        print("Knowledge Module Finished")
        return result

    PLANNER_PRIORITY_PREVIEW_LIMIT = 5

    def _resolve_planner_priority(
        self,
        planner_result: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        try:
            return self.planner_consumer_adapter.resolve_knowledge_priority(
                planner_result=planner_result,
                engine_default=[],
            )
        except Exception as error:
            print(f"Knowledge Planner Priority Resolution Failed: {error}")
            return {
                "hint_applied": False,
                "reason": f"priority_resolution_error: {error}",
                "knowledge_priority": [],
            }

    def _build_planner_priority_preview(
        self,
        ranked_items: List[Dict[str, Any]],
        priority_types: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Self Reference Guard (Sprint 16-0): 이 미리보기는 순수 진단용이다 -
        `ranked_items`의 실제 `overall_score`/순서를 그대로 읽기만 하고 절대
        수정하지 않는다. `KnowledgeRanker`가 이미 실제 점수 기준으로 매긴 순위를
        그대로 사용해, Planner가 우선순위로 지정한 타입에 해당하는 항목만
        골라서 보여준다 - "Planner Hint가 실제로 상위권과 얼마나 일치하는지"를
        투명하게 보여줄 뿐, 어떤 순위나 점수도 바꾸지 않는다. 이 결과는
        `top_knowledge`(Learning/Audit이 실제로 소비)와 완전히 분리되어 있으며
        storage에도 저장되지 않는다.
        """
        try:
            if not priority_types:
                return []

            priority_set = set(priority_types)
            matched = [
                {
                    "knowledge_id": item.get("knowledge_id"),
                    "type": item.get("type"),
                    "title": item.get("title"),
                    "overall_score": (item.get("score") or {}).get("overall_score", 0.0),
                    "rank": item.get("rank"),
                }
                for item in ranked_items
                if item.get("type") in priority_set
            ]
            return matched[: self.PLANNER_PRIORITY_PREVIEW_LIMIT]
        except Exception as error:
            print(f"Knowledge Planner Priority Preview Failed: {error}")
            return []

    def _build_result(
        self,
        context: Dict[str, Any],
        planner_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        extracted_items = self.extractor.extract(context)
        classified_items = self.classifier.classify(extracted_items, context)
        checked_items = self.duplicate_detector.check(classified_items)
        scored_items = self.scorer.score(checked_items, context)
        ranked_items = self.ranker.rank(scored_items)

        planner_priority_resolution = self._resolve_planner_priority(planner_result)
        planner_priority_preview = self._build_planner_priority_preview(
            ranked_items, planner_priority_resolution.get("knowledge_priority", [])
        )

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

        planner_requested_priority = (
            planner_result.get("knowledge_priority") if isinstance(planner_result, dict) else None
        )

        return {
            "status": "knowledge_extracted",
            "extracted_count": len(ranked_items),
            "new_count": upsert_summary.get("new_count", 0),
            "updated_count": upsert_summary.get("updated_count", 0),
            "total_knowledge_count": upsert_summary.get("total_count", 0),
            "by_type": by_type_count,
            "top_knowledge": top_knowledge,
            "planner_priority_preview": planner_priority_preview,
            "statistics": statistics,
            "fallback_used": run_fallback_used,
            "reason": "",
            "planner_consumption": {
                "knowledge": build_consumption_metadata(
                    planner_result=planner_result,
                    hint_applied=bool(planner_priority_resolution.get("hint_applied")),
                    requested_value=planner_requested_priority,
                    original_value=[],
                    final_value=planner_priority_resolution.get("knowledge_priority", []),
                    reason=planner_priority_resolution.get("reason", ""),
                ),
            },
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
            "planner_priority_preview": [],
            "statistics": statistics,
            "fallback_used": True,
            "reason": reason,
            "created_at": datetime.now().isoformat(),
        }
