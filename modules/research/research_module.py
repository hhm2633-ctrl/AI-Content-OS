import json
from datetime import datetime
from pathlib import Path

from src.llm_client import LLMClient
from modules.knowledge_engine.knowledge_interface import KnowledgeInterface
from modules.research.research_context_builder import ResearchContextBuilder
from modules.research.research_insight_generator import ResearchInsightGenerator


class ResearchModule:
    def __init__(self, config=None, llm_client=None):
        self.config = config or {}
        self.output_dir = Path("storage/research")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.selected_topic_path = Path("storage/trends/selected_topic.json")
        self.pattern_result_path = Path("storage/pattern/pattern_result.json")

        if llm_client is not None:
            self.llm_client = llm_client
        else:
            try:
                self.llm_client = LLMClient(self.config.get("llm", self.config))
            except Exception as error:
                print(f"Research LLM Client Init Failed: {error}")
                self.llm_client = None

        self.context_builder = ResearchContextBuilder(self.config)
        self.insight_generator = ResearchInsightGenerator(self.config, self.llm_client)

        # Knowledge Interface 실제 연결(Sprint 12): 리서치 로직은 그대로 두고,
        # 축적된 Knowledge DB의 funnel/workflow 참고 정보만 결과에 덧붙인다.
        self.knowledge_interface = KnowledgeInterface()

    def run(self, topic_result=None):
        print("Research Module Started")

        keyword = "AI content automation"
        title = "AI content automation card news topic"

        try:
            topic_result = topic_result or {}
            selected_topic = self._load_selected_topic() or topic_result.get("selected_topic", {})
            pattern_result = self._load_pattern_result()

            keyword = (
                selected_topic.get("title")
                or selected_topic.get("keyword")
                or "AI content automation"
            )
            title = selected_topic.get("title", f"{keyword} card news topic")

            research_context = self.context_builder.build(selected_topic, pattern_result)
            insight_result = self.insight_generator.generate(
                keyword=keyword,
                title=title,
                research_context=research_context,
            )

            result = {
                "status": "success",
                "message": "research_completed",
                "keyword": keyword,
                "title": title,
                "summary": insight_result.get(
                    "summary",
                    f"{keyword} is a useful topic for card news, blog, and shorts content automation.",
                ),
                "key_points": insight_result.get(
                    "key_points",
                    [
                        f"{keyword} can attract beginners interested in practical automation.",
                        "It is suitable for a short and clear card news format.",
                        "It can connect naturally to Instagram content operations.",
                        "It can later expand into blog, shorts, and product-linked content.",
                    ],
                ),
                "topic_angle": selected_topic.get("angle", ""),
                "target": selected_topic.get("target", ""),
                "source": selected_topic.get("source", "local"),
                "quality_score": selected_topic.get("quality_score"),
                "selection_reason": selected_topic.get("selection_reason", ""),
                "collection_method": selected_topic.get("collection_method", ""),
                "selected_topic_source": (
                    "selected_topic_json"
                    if selected_topic.get("_loaded_from_selected_topic_json")
                    else "topic_result"
                ),
                "topic_intelligence": pattern_result.get("topic_intelligence", {}),
                "pattern_plan": pattern_result.get("pattern_plan", {}),
                "pattern_result_available": bool(pattern_result),
                "research_context": research_context,
                "research_insight": {
                    "issue_background": insight_result.get("issue_background", ""),
                    "why_trending_now": insight_result.get("why_trending_now", ""),
                    "audience_interest_points": insight_result.get("audience_interest_points", []),
                    "caution_expressions": insight_result.get("caution_expressions", []),
                    "insight_source": insight_result.get("insight_source", "fallback"),
                    "fallback_used": insight_result.get("fallback_used", True),
                    "reason": insight_result.get("reason", ""),
                },
                "created_at": datetime.now().isoformat(),
            }

            result["knowledge_reference"] = self._build_knowledge_reference()

            self._save_result(result)

            print("Research Module Finished")
            return result
        except Exception as error:
            print(f"Research Module Failed, fallback result returned: {error}")

            result = self._fallback_result(
                keyword=keyword,
                title=title,
                reason=f"research_module_exception: {error}",
            )

            print("Research Module Finished")
            return result

    def _fallback_result(self, keyword, title, reason):
        return {
            "status": "success",
            "message": "research_completed",
            "keyword": keyword,
            "title": title,
            "summary": f"{keyword} is a useful topic for card news, blog, and shorts content automation.",
            "key_points": [
                f"{keyword} can attract beginners interested in practical automation.",
                "It is suitable for a short and clear card news format.",
                "It can connect naturally to Instagram content operations.",
                "It can later expand into blog, shorts, and product-linked content.",
            ],
            "topic_angle": "",
            "target": "",
            "source": "fallback",
            "quality_score": None,
            "selection_reason": "",
            "collection_method": "",
            "selected_topic_source": "fallback",
            "topic_intelligence": {},
            "pattern_plan": {},
            "pattern_result_available": False,
            "research_context": {
                "keyword": keyword,
                "category": "",
                "cluster": "",
                "confidence_score": None,
                "quality_score": None,
                "selection_reason": "",
                "source_signals": {},
                "fallback_sources": [],
                "trend_engine_status": {},
                "reason": f"Research Module 예외로 fallback context 사용: {reason}",
                "fallback_used": True,
            },
            "research_insight": {
                "issue_background": f"{keyword} 관련 논의가 여러 채널에서 꾸준히 이어지고 있습니다.",
                "why_trending_now": f"{keyword}에 대한 관심이 최근 트렌드 수집 신호에서 반복적으로 확인되고 있습니다.",
                "audience_interest_points": [
                    f"{keyword}를 처음 시작하는 방법",
                    f"{keyword}로 시간을 아끼는 방법",
                ],
                "caution_expressions": ["대박", "무조건", "100% 보장", "확정 수익"],
                "insight_source": "fallback",
                "fallback_used": True,
                "reason": f"Research Module 예외로 fallback 사용: {reason}",
            },
            "knowledge_reference": self._build_knowledge_reference(),
            "created_at": datetime.now().isoformat(),
        }

    def _build_knowledge_reference(self) -> dict:
        try:
            return {
                "top_funnels": self.knowledge_interface.get_funnel_knowledge(limit=3),
                "top_workflow_signals": self.knowledge_interface.get_workflow_knowledge(limit=3),
            }
        except Exception as error:
            print(f"Research Knowledge Reference Failed: {error}")
            return {"top_funnels": [], "top_workflow_signals": []}

    def _load_selected_topic(self):
        if not self.selected_topic_path.exists():
            return None

        try:
            with open(self.selected_topic_path, "r", encoding="utf-8") as file:
                selected_topic = json.load(file)

            if not isinstance(selected_topic, dict):
                return None

            title = str(selected_topic.get("title", "")).strip()

            if not title:
                return None

            selected_topic["_loaded_from_selected_topic_json"] = True
            return selected_topic

        except Exception as error:
            print(f"Selected Topic Load Failed: {error}")
            return None

    def _load_pattern_result(self):
        if not self.pattern_result_path.exists():
            return {}

        try:
            with open(self.pattern_result_path, "r", encoding="utf-8") as file:
                pattern_result = json.load(file)

            if not isinstance(pattern_result, dict):
                return {}

            return pattern_result

        except Exception as error:
            print(f"Pattern Result Load Failed: {error}")
            return {}

    def _save_result(self, result):
        file_path = self.output_dir / "research_result.json"

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)

        print(f"Research Result Saved: {file_path}")
