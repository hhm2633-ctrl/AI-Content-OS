import json
from pathlib import Path

from modules.trend_collector.trend_collector_module import TrendCollectorModule
from modules.topic_engine.topic_engine_module import TopicEngineModule
from modules.pattern_engine.pattern_engine_module import PatternEngineModule
from modules.pattern_engine.pattern_result_writer import PatternResultWriter
from modules.research.research_module import ResearchModule
from modules.content.content_module import ContentModule
from modules.image_strategy.image_strategy_module import ImageStrategyModule
from modules.image_prompt.image_prompt_module import ImagePromptModule
from modules.image_generation.image_generation_module import ImageGenerationModule
from modules.card_news.card_news_module import CardNewsModule
from modules.publishing.publishing_module import PublishingModule
from modules.knowledge_engine.knowledge_module import KnowledgeModule
from modules.performance_score.performance_score_module import PerformanceScoreModule
from modules.audit_engine.audit_engine_module import AuditEngineModule
from modules.learning_engine.learning_engine_module import LearningEngineModule
from modules.analytics_engine.analytics_engine_module import AnalyticsEngineModule
from modules.brand_dna_engine.brand_dna_engine_module import BrandDNAEngineModule
from modules.trend_memory.trend_memory_module import TrendMemoryModule
from modules.competitor_engine.competitor_engine_module import CompetitorEngineModule


class WorkflowEngine:
    def __init__(self, config=None):
        self.config = config or {}
        self.output_dir = Path("storage/workflow_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.trend_collector = TrendCollectorModule(self.config)
        self.topic_engine = TopicEngineModule(self.config)
        # AI Planner (Sprint 15-0, Architecture Only): future connection point.
        # self.ai_planner_module = AIPlannerModule(self.config) will be instantiated
        # here once a real Decision Engine exists. Not instantiated yet - see
        # modules/ai_planner/planner_contract.py (PlannerContract.WORKFLOW_INTEGRATION_NOTE).
        self.pattern_engine = PatternEngineModule(self.config)
        self.research_module = ResearchModule(self.config)
        self.content_module = ContentModule(self.config)
        self.image_strategy_module = ImageStrategyModule(self.config)
        self.image_prompt_module = ImagePromptModule(self.config)
        self.image_generation_module = ImageGenerationModule(self.config)
        self.card_news_module = CardNewsModule(self.config)
        self.publishing_module = PublishingModule(self.config)
        self.knowledge_module = KnowledgeModule(self.config)
        self.performance_score_module = PerformanceScoreModule(self.config)
        self.audit_engine_module = AuditEngineModule(self.config)
        self.learning_engine_module = LearningEngineModule(self.config)
        self.analytics_engine_module = AnalyticsEngineModule(self.config)
        self.brand_dna_engine_module = BrandDNAEngineModule(self.config)
        self.trend_memory_module = TrendMemoryModule(self.config)
        self.competitor_engine_module = CompetitorEngineModule(self.config)

    def run(self):
        print("=" * 50)
        print("Workflow Engine Started")
        print("=" * 50)

        try:
            trend_result = self.trend_collector.run()
            self._save_workflow_result("01_trend_result.json", trend_result)

            topic_result = self.topic_engine.run(trend_result)
            self._save_workflow_result("02_topic_result.json", topic_result)

            # AI Planner (Sprint 15-0, Architecture Only): future connection point.
            # planner_result = self.ai_planner_module.run(PlanningContext(...)) would run
            # here, after TopicEngineModule and before PatternEngineModule, so its
            # coordination decisions (pattern/hook/cta/image_strategy/content_strategy)
            # could inform the Engines that follow. Not connected yet - no Decision
            # Engine exists (modules/ai_planner/planner_module.py is a Skeleton only).

            pattern_result = self._run_pattern_engine(topic_result, trend_result)
            self._save_workflow_result("03_pattern_result.json", pattern_result)

            research_result = self.research_module.run(topic_result)
            self._save_workflow_result("04_research_result.json", research_result)

            content_result = self.content_module.run(research_result)
            self._save_workflow_result("05_content_result.json", content_result)

            image_strategy_result = self.image_strategy_module.run(content_result, research_result)
            self._save_workflow_result("05b_image_strategy_result.json", image_strategy_result)

            image_prompt_result = self.image_prompt_module.run(content_result, image_strategy_result)
            self._save_workflow_result("06_image_prompt_result.json", image_prompt_result)

            image_generation_result = self.image_generation_module.run(image_prompt_result)
            self._save_workflow_result("07_image_generation_result.json", image_generation_result)

            card_news_result = self.card_news_module.run(
                content_result,
                image_generation_result,
                image_strategy_result
            )
            self._save_workflow_result("08_card_news_result.json", card_news_result)

            publishing_result = self.publishing_module.run(card_news_result)
            self._save_workflow_result("09_publishing_result.json", publishing_result)

            knowledge_result = self._run_knowledge_engine(
                trend_result=trend_result,
                topic_result=topic_result,
                pattern_result=pattern_result,
                research_result=research_result,
                content_result=content_result,
                image_strategy_result=image_strategy_result,
                card_news_result=card_news_result,
                publishing_result=publishing_result,
            )
            self._save_workflow_result("10_knowledge_result.json", knowledge_result)

            # Trend Memory는 Audit Engine의 duplicate_check가 topic_repeat_risk를
            # 함께 참고할 수 있도록 Performance Score/Audit보다 먼저 실행한다.
            trend_memory_result = self._run_safe(
                "Trend Memory Engine",
                self._empty_trend_memory_result,
                self.trend_memory_module.run,
                pattern_result=pattern_result,
                card_news_result=card_news_result,
                image_strategy_result=image_strategy_result,
            )
            self._save_workflow_result("11_trend_memory_result.json", trend_memory_result)

            performance_score_result = self._run_safe(
                "Performance Score Engine",
                self._empty_performance_score_result,
                self.performance_score_module.run,
                content_result=content_result,
                card_news_result=card_news_result,
                image_strategy_result=image_strategy_result,
            )
            self._save_workflow_result("12_performance_score_result.json", performance_score_result)

            audit_result = self._run_safe(
                "Audit Engine",
                self._empty_audit_result,
                self.audit_engine_module.run,
                content_result=content_result,
                pattern_result=pattern_result,
                card_news_result=card_news_result,
                image_strategy_result=image_strategy_result,
                performance_score_result=performance_score_result,
                knowledge_result=knowledge_result,
                trend_memory_result=trend_memory_result,
            )
            self._save_workflow_result("13_audit_result.json", audit_result)

            learning_result = self._run_safe(
                "Learning Engine",
                self._empty_learning_result,
                self.learning_engine_module.run,
                knowledge_result=knowledge_result,
                performance_score_result=performance_score_result,
                audit_result=audit_result,
            )
            self._save_workflow_result("14_learning_result.json", learning_result)

            analytics_result = self._run_safe(
                "Analytics Engine",
                self._empty_analytics_result,
                self.analytics_engine_module.run,
                performance_score_result=performance_score_result,
                audit_result=audit_result,
            )
            self._save_workflow_result("15_analytics_result.json", analytics_result)

            brand_dna_result = self._run_safe(
                "Brand DNA Engine",
                self._empty_brand_dna_result,
                self.brand_dna_engine_module.run,
                pattern_result=pattern_result,
                content_result=content_result,
                card_news_result=card_news_result,
            )
            self._save_workflow_result("16_brand_dna_result.json", brand_dna_result)

            competitor_result = self._run_safe(
                "Competitor Engine",
                self._empty_competitor_result,
                self.competitor_engine_module.run,
            )
            self._save_workflow_result("17_competitor_result.json", competitor_result)

            final_result = {
                "status": "workflow_completed",
                "trend": trend_result,
                "topic": topic_result,
                "pattern": pattern_result,
                "research": research_result,
                "content": content_result,
                "image_strategy": image_strategy_result,
                "image_prompt": image_prompt_result,
                "image_generation": image_generation_result,
                "card_news": card_news_result,
                "publishing": publishing_result,
                "knowledge": knowledge_result,
                "performance_score": performance_score_result,
                "audit": audit_result,
                "learning": learning_result,
                "analytics": analytics_result,
                "brand_dna": brand_dna_result,
                "trend_memory": trend_memory_result,
                "competitor": competitor_result
            }

            self._save_workflow_result("99_final_result.json", final_result)

            print("=" * 50)
            print("workflow_completed")
            print("=" * 50)

            return final_result

        except Exception as error:
            error_result = {
                "status": "workflow_failed",
                "error": str(error)
            }

            self._save_workflow_result("00_workflow_error.json", error_result)

            print("=" * 50)
            print("workflow_failed")
            print(str(error))
            print("=" * 50)

            return error_result

    def _run_pattern_engine(self, topic_result, trend_result):
        try:
            selected_topic = {}

            if isinstance(topic_result, dict):
                selected_topic = topic_result.get("selected_topic", {})

            return self.pattern_engine.run(
                selected_topic=selected_topic,
                trend_result=trend_result,
            )

        except Exception as error:
            pattern_result = {
                "status": "pattern_selected",
                "selected_topic": {},
                "topic_intelligence": {
                    "keywords": [],
                    "keyword_weights": {},
                    "category": "trend",
                    "cluster": "general_trend_cluster",
                    "confidence_score": 0.0,
                    "reason": f"fallback: pattern_engine_error: {error}",
                },
                "pattern_plan": {
                    "pattern_type": "resource",
                    "hook_type": "saveable_tip",
                    "cta_type": "save",
                    "layout_type": "bold_ai",
                    "reason": "PatternEngineModule failed; safe default pattern used.",
                },
                "fallback_used": True,
            }

            try:
                PatternResultWriter().write(pattern_result)
            except Exception as write_error:
                print(f"Pattern Fallback Write Failed: {write_error}")

            print(f"Pattern Engine Fallback Used: {error}")
            return pattern_result

    def _run_knowledge_engine(
        self,
        trend_result,
        topic_result,
        pattern_result,
        research_result,
        content_result,
        image_strategy_result,
        card_news_result,
        publishing_result,
    ):
        try:
            return self.knowledge_module.run(
                pattern_result=pattern_result,
                research_result=research_result,
                content_result=content_result,
                image_strategy_result=image_strategy_result,
                card_news_result=card_news_result,
                publishing_result=publishing_result,
                trend_result=trend_result,
                topic_result=topic_result,
            )
        except Exception as error:
            print(f"Knowledge Engine Fallback Used: {error}")
            return {
                "status": "knowledge_extracted",
                "extracted_count": 0,
                "new_count": 0,
                "updated_count": 0,
                "total_knowledge_count": 0,
                "by_type": {},
                "top_knowledge": [],
                "statistics": {},
                "fallback_used": True,
                "reason": f"knowledge_engine_error: {error}",
            }

    def _run_safe(self, engine_label, empty_result_fn, run_fn, **kwargs):
        """
        Sprint 12에서 추가된 Engine들의 공용 안전 실행 래퍼. 각 Engine의 run()이
        자체적으로 내부 fallback을 갖추고 있어도, WorkflowEngine 레벨에서 한 번 더
        try/except로 감싸 어떤 Engine 하나가 완전히 실패하더라도 workflow_failed로
        이어지지 않고 안전한 기본 결과로 다음 단계가 계속 진행되도록 한다
        (Pattern Engine/Knowledge Engine과 동일한 이중 안전망 패턴).
        """
        try:
            return run_fn(**kwargs)
        except Exception as error:
            print(f"{engine_label} Fallback Used: {error}")
            return empty_result_fn(reason=f"{engine_label.lower().replace(' ', '_')}_error: {error}")

    def _empty_performance_score_result(self, reason):
        return {
            "status": "performance_score_completed",
            "hook_score": 0.5, "cta_score": 0.5, "layout_score": 0.5,
            "brand_score": 0.5, "image_score": 0.5, "overall_performance_score": 0.5,
            "fallback_used": True,
            "reason": reason,
        }

    def _empty_audit_result(self, reason):
        return {
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
        }

    def _empty_learning_result(self, reason):
        return {
            "status": "learning_completed",
            "internal_learning_score": 0.0,
            "audit_score": 0.0,
            "performance_score": 0.0,
            "knowledge_score": 0.0,
            "is_good_run": False,
            "promoted_count": 0,
            "promoted_entries": [],
            "total_memory_count": 0,
            "knowledge_used": False,
            "knowledge_items": [],
            "knowledge_influence": "",
            "fallback_used": True,
            "reason": reason,
        }

    def _empty_analytics_result(self, reason):
        return {
            "status": "analytics_completed",
            "current_performance_score": 0.0,
            "current_audit_score": 0.0,
            "historical_average_performance_score": None,
            "sample_size": 0,
            "quality_trend": "insufficient_history",
            "fallback_used": True,
            "reason": reason,
        }

    def _empty_brand_dna_result(self, reason):
        return {
            "status": "brand_dna_updated",
            "brand_profile": {},
            "observation": {},
            "dominant_hook_type": "",
            "dominant_cta_type": "",
            "dominant_layout_type": "",
            "dominant_color": "",
            "total_observations": 0,
            "fallback_used": True,
            "reason": reason,
        }

    def _empty_trend_memory_result(self, reason):
        return {
            "status": "trend_memory_recorded",
            "current": {},
            "topic_repeat_risk": "low",
            "topic_similarity": 0.0,
            "matched_topic": "",
            "element_repeat_counts": {},
            "total_memory_count": 0,
            "fallback_used": True,
            "reason": reason,
        }

    def _empty_competitor_result(self, reason):
        return {
            "status": "competitor_profile_built",
            "benchmark": {"status": "benchmark_unavailable", "sections": [], "fallback_used": True},
            "community": {"status": "community_unavailable", "sources": [], "fallback_used": True},
            "news": {"status": "news_unavailable", "source": {}, "fallback_used": True},
            "instagram_benchmark": {"status": "instagram_benchmark_unavailable", "accounts": [], "fallback_used": True},
            "tools_funnel": {"status": "tools_funnel_unavailable", "references": [], "fallback_used": True},
            "account_profiles": [],
            "hook_and_cta_map": {"hook_sections": [], "cta_sections": []},
            "repeated_content_patterns": [],
            "format_comparison": {
                "status": "no_account_profiles",
                "account_count": 0,
                "layout_distribution": {},
                "cta_distribution": {},
                "image_strategy_distribution": {},
            },
            "gap_analysis_input": {
                "benchmark_hook_count": 0,
                "benchmark_cta_count": 0,
                "community_signal_available": False,
                "news_signal_available": False,
                "account_profile_count": 0,
                "high_priority_account_count": 0,
            },
            "fallback_used": True,
            "reason": reason,
        }

    def _save_workflow_result(self, filename, data):
        file_path = self.output_dir / filename

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        print(f"Workflow Result Saved: {file_path}")
