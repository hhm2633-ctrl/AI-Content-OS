import unittest
from pathlib import Path
from unittest.mock import patch

from modules.ai_planner.planner_module import AIPlannerModule
from modules.card_news.card_news_module import CardNewsModule
from modules.content.content_prompt_builder import ContentPromptBuilder
from modules.image_strategy.image_strategy_module import ImageStrategyModule
from modules.knowledge_engine.knowledge_module import KnowledgeModule
from modules.pattern_engine.hook_selector import HookSelector
from modules.pattern_engine.cta_selector import CTASelector
from modules.pattern_engine.pattern_engine_module import PatternEngineModule
from modules.pattern_engine.pattern_selector import PatternSelector
from modules.publishing.publishing_module import PublishingModule
from src.workflow_engine import WorkflowEngine

REPO_ROOT = Path(__file__).resolve().parents[1]


class _WorkflowEngineAIPlannerStub(object):
    """
    `WorkflowEngine._run_ai_planner`/`_run_pattern_engine`는 unbound 메서드로
    호출해도 `self.ai_planner_module`/`self.pattern_engine`만 있으면 그대로
    동작한다. 실제 `WorkflowEngine()`을 통째로 생성하면 `ContentModule`이
    `LLMClient`(OPENAI_API_KEY 필요)까지 함께 생성되어 테스트 환경에 API 키가
    없으면 실패한다 - 이 테스트는 네트워크/LLM을 쓰지 않아야 하므로, 필요한
    두 속성만 가진 가벼운 stub으로 대신한다(WorkflowEngine을 재구현하지 않고
    실제 메서드 코드를 그대로 재사용한다).
    """

    def __init__(self):
        self.ai_planner_module = AIPlannerModule()
        self.pattern_engine = PatternEngineModule()


def _decided_planner_result(**overrides):
    base = {
        "status": "planner_decided",
        "schema_valid": True,
        "selected_pattern": "tutorial",
        "selected_hook_strategy": "pain_point",
        "selected_cta_strategy": "follow",
        "selected_image_strategy": "ai_tools",
        "knowledge_priority": ["cta", "hook"],
        "competitor_reference": ["some_account"],
        "content_strategy": "Focus on beginner-friendly automation framing.",
        "planner_confidence": 0.8,
        "planner_reason": "test fixture",
        "planner_version": "0.3.0-decision-v1",
    }
    base.update(overrides)
    return base


AI_TOPIC_SELECTED_TOPIC = {
    "keyword": "ChatGPT 자동화",
    "title": "ChatGPT 자동화 지금 시작해야 하는 이유",
    "quality_score": 80,
}


class TestWorkflowEngineAIPlannerWiring(unittest.TestCase):
    """
    Sprint 15-3 Workflow Integration 테스트. 외부 API/LLM/네트워크를 사용하지
    않는다 - `WorkflowEngine.run()` 전체를 실행하지 않고(Trend Collector 등
    네트워크에 의존하는 단계가 있으므로), Planner 실행 위치/전달과 각 Consumer
    Engine의 소비 로직만 격리해서 직접 검증한다. 전체 workflow_completed 회귀는
    `py -m src.main`으로 별도 확인한다.
    """

    # ---- Planner 실행 위치 (실제 소스 순서) ----

    def test_workflow_engine_calls_planner_before_pattern_engine(self):
        source = (REPO_ROOT / "src" / "workflow_engine.py").read_text(encoding="utf-8")
        code_only = "\n".join(line for line in source.splitlines() if not line.strip().startswith("#"))

        self.assertLess(
            code_only.index("self._run_ai_planner("),
            code_only.index("self._run_pattern_engine("),
        )

    # ---- Planner Exception/None Recovery ----

    def test_run_ai_planner_returns_none_on_exception(self):
        stub = _WorkflowEngineAIPlannerStub()

        with patch.object(stub.ai_planner_module, "run", side_effect=RuntimeError("boom")):
            result = WorkflowEngine._run_ai_planner(
                stub, {"trends": []}, {"selected_topic": AI_TOPIC_SELECTED_TOPIC}
            )

        self.assertIsNone(result)

    def test_run_ai_planner_returns_dict_on_success(self):
        stub = _WorkflowEngineAIPlannerStub()

        result = WorkflowEngine._run_ai_planner(
            stub,
            {"trends": [{"keyword": "ChatGPT 자동화", "quality_score": 80}]},
            {"selected_topic": AI_TOPIC_SELECTED_TOPIC},
        )

        self.assertIsInstance(result, dict)
        self.assertIn("status", result)

    def test_run_pattern_engine_accepts_none_planner_result(self):
        stub = _WorkflowEngineAIPlannerStub()

        try:
            result = WorkflowEngine._run_pattern_engine(
                stub, {"selected_topic": AI_TOPIC_SELECTED_TOPIC}, {"trends": []}, planner_result=None
            )
        except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
            self.fail(f"_run_pattern_engine raised with planner_result=None: {error}")

        self.assertEqual(result["status"], "pattern_selected")

    # ---- Pattern Consumer 호출 + Metadata ----

    def test_pattern_engine_applies_planner_hint_and_records_metadata(self):
        module = PatternEngineModule()
        planner_result = _decided_planner_result()

        result = module.run(
            selected_topic=AI_TOPIC_SELECTED_TOPIC,
            trend_result={"trends": [{"keyword": "ChatGPT 자동화", "quality_score": 80}]},
            planner_result=planner_result,
        )

        consumption = result["planner_consumption"]["pattern"]
        self.assertIn(result["pattern_plan"]["pattern_type"], PatternSelector.PATTERN_TYPES)
        self.assertIsInstance(consumption["planner_applied"], bool)
        self.assertIn("planner_mode", consumption)

    def test_pattern_engine_identical_pattern_type_with_and_without_planner(self):
        """
        낮은 confidence의 Planner 결과는 게이트를 통과하지 못해 Hint가 거부되어야
        한다 - Planner가 있든 없든 최종 pattern_type이 동일해야
        "Planner 제거 시 Workflow가 깨지지 않는다"를 만족한다.
        """
        module = PatternEngineModule()
        selected_topic = AI_TOPIC_SELECTED_TOPIC
        trend_result = {"trends": [{"keyword": "ChatGPT 자동화", "quality_score": 80}]}

        without_planner = module.run(selected_topic=selected_topic, trend_result=trend_result, planner_result=None)
        with_low_confidence_planner = module.run(
            selected_topic=selected_topic,
            trend_result=trend_result,
            planner_result=_decided_planner_result(planner_confidence=0.05),
        )

        self.assertEqual(
            without_planner["pattern_plan"]["pattern_type"],
            with_low_confidence_planner["pattern_plan"]["pattern_type"],
        )
        self.assertFalse(with_low_confidence_planner["planner_consumption"]["pattern"]["planner_applied"])

    def test_pattern_engine_blocked_category_rejects_hint(self):
        """
        TopicClassifier가 차단 카테고리(예: 도박)로 분류하면 blocked=True가 되고,
        PlannerConsumerAdapter.resolve_pattern()의 안전 규칙 게이트에 의해
        planner_confidence가 아무리 높아도 Hint가 거부되어야 한다.
        """
        module = PatternEngineModule()
        blocked_topic = {"keyword": "토토 베팅 사이트 추천", "title": "토토 베팅 사이트 추천 순위"}

        result = module.run(
            selected_topic=blocked_topic,
            trend_result={"trends": []},
            planner_result=_decided_planner_result(planner_confidence=0.99),
        )

        self.assertTrue(result["topic_intelligence"]["blocked"])
        self.assertFalse(result["planner_consumption"]["pattern"]["planner_applied"])

    def test_pattern_engine_handles_malformed_planner_result(self):
        module = PatternEngineModule()

        for garbage in [None, "not a dict", 123, {"planner_confidence": object()}]:
            try:
                result = module.run(
                    selected_topic=AI_TOPIC_SELECTED_TOPIC,
                    trend_result={"trends": []},
                    planner_result=garbage,
                )
            except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
                self.fail(f"PatternEngineModule.run raised for planner_result={garbage!r}: {error}")

            self.assertEqual(result["status"], "pattern_selected")

    # ---- Content Consumer 호출 + Metadata ----

    def _research_result_with_pattern_plan(self, pattern_type="tutorial"):
        return {
            "keyword": "ChatGPT 자동화",
            "title": "ChatGPT 자동화 지금 시작해야 하는 이유",
            "pattern_plan": {
                "pattern_type": pattern_type,
                "hook_type": "beginner",
                "cta_type": "follow",
                "layout_type": "bold_ai",
                "reason": "test fixture",
            },
            "topic_intelligence": {
                "category": "AI",
                "cluster": "ai_automation_cluster",
                "confidence_score": 0.8,
                "blocked": False,
                "keywords": ["chatgpt", "자동화"],
            },
        }

    def test_content_prompt_builder_applies_hook_cta_hint_and_records_metadata(self):
        builder = ContentPromptBuilder()
        planner_result = _decided_planner_result()

        built = builder.build(self._research_result_with_pattern_plan(), planner_result)

        self.assertIsNotNone(built)
        consumption = built["meta"]["planner_consumption"]
        self.assertIn("hook", consumption)
        self.assertIn("cta", consumption)
        self.assertIn("content_strategy", consumption)
        self.assertIn(built["meta"]["hook_type"], HookSelector.HOOK_TYPES + ["beginner", "result_proof"])
        self.assertIn(built["meta"]["cta_type"], CTASelector.CTA_TYPES + ["share", "link_click"])

    def test_content_prompt_builder_handles_none_and_malformed_planner_result(self):
        builder = ContentPromptBuilder()
        research_result = self._research_result_with_pattern_plan()

        for garbage in [None, "not a dict", 123]:
            try:
                built = builder.build(research_result, garbage)
            except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
                self.fail(f"ContentPromptBuilder.build raised for planner_result={garbage!r}: {error}")

            self.assertIsNotNone(built)
            self.assertFalse(built["meta"]["planner_consumption"]["hook"]["planner_applied"])

    def test_content_prompt_builder_blocked_category_rejects_hint(self):
        builder = ContentPromptBuilder()
        research_result = self._research_result_with_pattern_plan()
        research_result["topic_intelligence"]["blocked"] = True

        built = builder.build(research_result, _decided_planner_result())

        self.assertFalse(built["meta"]["planner_consumption"]["hook"]["planner_applied"])
        self.assertFalse(built["meta"]["planner_consumption"]["cta"]["planner_applied"])

    # ---- Image Strategy Consumer 호출 + Metadata ----

    def test_image_strategy_module_applies_hint_and_preserves_real_image_priority(self):
        module = ImageStrategyModule()
        planner_result = _decided_planner_result(selected_image_strategy="news")

        result = module.run(
            content_result={"title": "테스트"},
            research_result={"source": "naver_news", "collection_method": "live_collect"},
            planner_result=planner_result,
        )

        consumption = result["planner_consumption"]["image_strategy"]
        self.assertIn("planner_applied", consumption)
        # AI Image 강제 금지: need_ai_image은 여전히 ImageSourceSelector/AIImageDecision의
        # 실제 우선순위 체인으로만 결정되어야 한다 (Planner가 need_ai_image 자체를
        # 직접 설정할 방법이 없다).
        self.assertIn("need_ai_image", result)
        self.assertIsInstance(result["need_ai_image"], bool)

    def test_image_strategy_module_handles_none_planner_result(self):
        module = ImageStrategyModule()

        try:
            result = module.run(content_result={}, research_result={}, planner_result=None)
        except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
            self.fail(f"ImageStrategyModule.run raised with planner_result=None: {error}")

        self.assertEqual(result["status"], "image_strategy_completed")
        self.assertFalse(result["planner_consumption"]["image_strategy"]["planner_applied"])

    # ---- Knowledge Consumer 호출 (Priority Preview, Sprint 16-0 이후 이름 변경) + Metadata ----
    # 참고: Sprint 15-3의 최초 구현은 이 hint를 실제 overall_score를 올리는
    # "Priority Boost"로 적용했으나, Sprint 16-0 Self Reference Guard에서 그
    # 방식이 Knowledge->Planner 순환 참조를 만든다는 것이 밝혀져 제거됐다. 지금은
    # 실제 점수를 전혀 바꾸지 않는 진단 전용 `planner_priority_preview`만 남는다
    # (자세한 내용은 tests/test_intelligence_feedback_safety.py 참고).

    def test_knowledge_module_records_planner_priority_consumption_without_removing_ranker(self):
        module = KnowledgeModule()
        planner_result = _decided_planner_result(knowledge_priority=["hook", "cta"])

        try:
            result = module.run(
                pattern_result={},
                research_result={},
                content_result={},
                image_strategy_result={},
                card_news_result={},
                publishing_result={},
                trend_result={},
                topic_result={},
                planner_result=planner_result,
            )
        except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
            self.fail(f"KnowledgeModule.run raised: {error}")

        self.assertEqual(result["status"], "knowledge_extracted")
        self.assertIn("knowledge", result["planner_consumption"])
        # KnowledgeRanker가 여전히 실제로 호출되고 있음을 간접 확인한다: 결과에
        # rank가 매겨진 top_knowledge 구조가 그대로 남아 있어야 한다.
        self.assertIn("top_knowledge", result)
        self.assertIn("planner_priority_preview", result)

    def test_knowledge_module_handles_none_planner_result(self):
        module = KnowledgeModule()

        try:
            result = module.run(planner_result=None)
        except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
            self.fail(f"KnowledgeModule.run raised with planner_result=None: {error}")

        self.assertEqual(result["status"], "knowledge_extracted")
        self.assertFalse(result["planner_consumption"]["knowledge"]["planner_applied"])

    # ---- CardNews/Publishing planner_influence 요약 (Codex 검수에서 발견된 버그의 회귀 테스트) ----

    def test_card_news_planner_influence_detects_content_only_hint(self):
        """
        회귀 테스트: `content_result["planner_consumption"]["content"]`는
        `image_strategy_result["planner_consumption"]["image_strategy"]`와 달리
        평평한 dict가 아니라 {"hook": {...}, "cta": {...}, "content_strategy": {...}}
        형태로 중첩되어 있다. Content만 Hint를 적용하고 Image Strategy는 적용하지
        않은 경우에도 `any_hint_applied`가 True여야 한다 - 최상위 키만 보면 항상
        False로 잘못 계산되는 버그가 있었다(Codex 검수에서 발견, 수정됨).
        """
        module = CardNewsModule()

        content_result = {
            "planner_consumption": {
                "content": {
                    "hook": {"planner_applied": True},
                    "cta": {"planner_applied": False},
                    "content_strategy": {"planner_applied": False},
                }
            }
        }
        image_strategy_result = {
            "planner_consumption": {
                "image_strategy": {"planner_applied": False},
            }
        }

        influence = module._build_planner_influence(content_result, image_strategy_result)

        self.assertTrue(influence["any_hint_applied"])

    def test_card_news_planner_influence_false_when_nothing_applied(self):
        module = CardNewsModule()

        content_result = {
            "planner_consumption": {
                "content": {
                    "hook": {"planner_applied": False},
                    "cta": {"planner_applied": False},
                    "content_strategy": {"planner_applied": False},
                }
            }
        }
        image_strategy_result = {"planner_consumption": {"image_strategy": {"planner_applied": False}}}

        influence = module._build_planner_influence(content_result, image_strategy_result)

        self.assertFalse(influence["any_hint_applied"])

    def test_publishing_module_copies_card_news_planner_influence(self):
        module = PublishingModule()
        card_news_result = {
            "cards": [],
            "title": "테스트",
            "planner_influence": {
                "any_hint_applied": True,
                "content": {"hook": {"planner_applied": True}},
                "image_strategy": {"planner_applied": False},
            },
        }

        strategy = module._resolve_planner_strategy(card_news_result)

        self.assertTrue(strategy["any_hint_applied"])

    def test_publishing_module_planner_strategy_defaults_when_missing(self):
        module = PublishingModule()

        strategy = module._resolve_planner_strategy({"cards": []})

        self.assertFalse(strategy["any_hint_applied"])


if __name__ == "__main__":
    unittest.main()
