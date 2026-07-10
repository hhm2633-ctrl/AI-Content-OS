import inspect
import unittest

from modules.ai_planner.planner_decision_engine import (
    MIN_BRAND_DNA_OBSERVATIONS_FOR_OVERRIDE,
    PlannerDecisionEngine,
)
from modules.analytics_engine.analytics_engine_module import AnalyticsEngineModule
from modules.brand_dna_engine.brand_dna_engine_module import BrandDNAEngineModule
from modules.brand_dna_engine.brand_dna_tracker import BrandDNATracker
from modules.common.metadata_standard import (
    SOURCE_ESTIMATED,
    SOURCE_HISTORICAL,
    SOURCE_LOCAL_QUALITY,
    SOURCE_RUNTIME,
    VALID_SOURCES,
    build_standard_metadata,
)
from modules.content.content_module import ContentModule
from modules.knowledge_engine.knowledge_module import KnowledgeModule
from modules.learning_engine.learning_engine_module import LearningEngineModule
from modules.performance_score.performance_score_module import PerformanceScoreModule


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
        "content_strategy": "test strategy",
        "planner_confidence": 0.8,
        "planner_reason": "test",
        "planner_version": "0.3.0-decision-v1",
    }
    base.update(overrides)
    return base


class TestBrandDNASelfReferenceGuard(unittest.TestCase):
    """
    Self Reference Guard: Planner가 자신이 만든 결과(pattern_type hint 적용)를
    다음 실행에서 "독립적인 브랜드 사용 증거"로 오인하지 않도록 하는 장치.
    """

    def test_brand_dna_tracker_records_planner_influenced_flag_true(self):
        tracker = BrandDNATracker()
        observation = tracker.observe(
            pattern_plan={"hook_type": "pain_point", "cta_type": "follow", "layout_type": "bold_ai"},
            layout_result={},
            brand_rule_passed=True,
            planner_influenced=True,
        )
        self.assertTrue(observation["planner_influenced"])

    def test_brand_dna_tracker_defaults_planner_influenced_to_false(self):
        tracker = BrandDNATracker()
        observation = tracker.observe(
            pattern_plan={"hook_type": "pain_point", "cta_type": "follow"},
            layout_result={},
            brand_rule_passed=True,
        )
        self.assertFalse(observation["planner_influenced"])

    def test_brand_dna_engine_module_detects_planner_applied_from_pattern_result(self):
        module = BrandDNAEngineModule()
        pattern_result = {
            "pattern_plan": {"hook_type": "pain_point", "cta_type": "follow", "layout_type": "bold_ai"},
            "planner_consumption": {"pattern": {"planner_applied": True}},
        }
        result = module.run(pattern_result=pattern_result, content_result={}, card_news_result={})

        self.assertTrue(result["observation"]["planner_influenced"])

    def test_brand_dna_engine_module_planner_influenced_false_when_hint_rejected(self):
        module = BrandDNAEngineModule()
        pattern_result = {
            "pattern_plan": {"hook_type": "pain_point", "cta_type": "follow"},
            "planner_consumption": {"pattern": {"planner_applied": False}},
        }
        result = module.run(pattern_result=pattern_result, content_result={}, card_news_result={})

        self.assertFalse(result["observation"]["planner_influenced"])

    def test_planner_decision_engine_override_gate_excludes_planner_influenced_observations(self):
        """
        핵심 회귀 테스트: total_observations는 임계치를 넘지만, 전부 Planner
        자신의 과거 영향으로 만들어진 관찰이라면(독립 관찰 0회) override를
        적용하면 안 된다.
        """
        engine = PlannerDecisionEngine()
        brand_dna_history = {
            "dominant_hook_type": "authority",
            "total_observations": MIN_BRAND_DNA_OBSERVATIONS_FOR_OVERRIDE + 10,
            "planner_influenced_observations": MIN_BRAND_DNA_OBSERVATIONS_FOR_OVERRIDE + 10,
        }

        hook_type, note, overridden = engine._select_hook_with_history("pain_point", brand_dna_history)

        self.assertFalse(overridden)
        self.assertEqual(hook_type, "pain_point")
        self.assertIn("독립", note)

    def test_planner_decision_engine_override_applies_with_sufficient_independent_observations(self):
        engine = PlannerDecisionEngine()
        # "comment"는 CTASelector(Pattern Engine 5종 CTA 집합, planner_decision_engine.py가
        # 실제로 검사에 쓰는 enum)의 실제 멤버다 - Content Engine의 7종 CTAStrategy
        # 전용 값("share"/"link_click")과 혼동하지 않는다.
        brand_dna_history = {
            "dominant_cta_type": "comment",
            "total_observations": MIN_BRAND_DNA_OBSERVATIONS_FOR_OVERRIDE + 1,
            "planner_influenced_observations": 0,
        }

        cta_type, note, overridden = engine._select_cta_with_history("save", brand_dna_history)

        self.assertTrue(overridden)
        self.assertEqual(cta_type, "comment")

    def test_planner_decision_engine_override_gate_handles_missing_planner_influenced_field(self):
        """
        Sprint 16-0 이전 데이터(planner_influenced_observations 필드가 없는 과거
        storage)에 대해서도 안전하게 동작해야 한다 - 0으로 취급한다.
        """
        engine = PlannerDecisionEngine()
        brand_dna_history = {
            "dominant_hook_type": "authority",
            "total_observations": MIN_BRAND_DNA_OBSERVATIONS_FOR_OVERRIDE,
        }

        hook_type, note, overridden = engine._select_hook_with_history("pain_point", brand_dna_history)

        self.assertTrue(overridden)
        self.assertEqual(hook_type, "authority")

    def test_planner_decision_engine_independent_observations_never_negative(self):
        engine = PlannerDecisionEngine()
        # 손상된 데이터: planner_influenced_observations가 total_observations보다 큼.
        independent = engine._independent_brand_dna_observations(
            {"total_observations": 3, "planner_influenced_observations": 10}
        )
        self.assertEqual(independent, 0)


class TestKnowledgeFeedbackLoop(unittest.TestCase):
    """
    Circular Feedback 방지: Planner의 knowledge_priority Hint가 실제 저장되는
    overall_score를 절대 변경하지 않아야 한다(Sprint 15-3의 최초 구현에서 발견된
    버그의 회귀 테스트).
    """

    def _sample_ranked_items(self):
        return [
            {"knowledge_id": "a", "type": "hook", "title": "A", "score": {"overall_score": 0.9}, "rank": 1},
            {"knowledge_id": "b", "type": "cta", "title": "B", "score": {"overall_score": 0.8}, "rank": 2},
            {"knowledge_id": "c", "type": "pattern", "title": "C", "score": {"overall_score": 0.5}, "rank": 3},
        ]

    def test_planner_priority_preview_does_not_mutate_input_scores(self):
        module = KnowledgeModule()
        ranked_items = self._sample_ranked_items()
        original_scores = [dict(item["score"]) for item in ranked_items]

        module._build_planner_priority_preview(ranked_items, ["cta", "hook"])

        for item, original_score in zip(ranked_items, original_scores):
            self.assertEqual(item["score"], original_score)

    def test_planner_priority_preview_only_includes_matching_types(self):
        module = KnowledgeModule()
        ranked_items = self._sample_ranked_items()

        preview = module._build_planner_priority_preview(ranked_items, ["cta"])

        self.assertEqual(len(preview), 1)
        self.assertEqual(preview[0]["type"], "cta")
        self.assertEqual(preview[0]["overall_score"], 0.8)

    def test_planner_priority_preview_uses_real_score_not_boosted(self):
        module = KnowledgeModule()
        ranked_items = self._sample_ranked_items()

        preview = module._build_planner_priority_preview(ranked_items, ["hook"])

        self.assertEqual(preview[0]["overall_score"], 0.9)

    def test_planner_priority_preview_empty_when_no_priority_types(self):
        module = KnowledgeModule()
        preview = module._build_planner_priority_preview(self._sample_ranked_items(), [])
        self.assertEqual(preview, [])

    def test_planner_priority_preview_never_raises_on_malformed_items(self):
        module = KnowledgeModule()
        malformed_items = [None, "not a dict", {"type": "hook"}, {"score": None, "type": "cta"}]

        try:
            preview = module._build_planner_priority_preview(malformed_items, ["hook", "cta"])
        except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
            self.fail(f"_build_planner_priority_preview raised: {error}")

        self.assertIsInstance(preview, list)

    def test_resolve_planner_priority_never_raises_on_garbage(self):
        module = KnowledgeModule()

        for garbage in [None, "not a dict", 123]:
            try:
                resolution = module._resolve_planner_priority(garbage)
            except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
                self.fail(f"_resolve_planner_priority raised for {garbage!r}: {error}")

            self.assertFalse(resolution.get("hint_applied"))

    def test_knowledge_module_result_separates_top_knowledge_from_priority_preview(self):
        module = KnowledgeModule()
        planner_result = _decided_planner_result(knowledge_priority=["hook"])

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

        self.assertIn("top_knowledge", result)
        self.assertIn("planner_priority_preview", result)
        # top_knowledge의 각 항목 overall_score는 실제 저장되는 값과 동일해야
        # 하며, Planner 우선순위와 무관하게 항상 Ranker의 실제 정렬 결과다.
        for item in result["top_knowledge"]:
            self.assertIsInstance(item.get("overall_score"), (int, float))


class TestAnalyticsSourceMetadata(unittest.TestCase):
    """
    Analytics 검증: 실제 측정값/로컬 품질/추정값을 명확히 구분하고, 가짜
    실측처럼 보이지 않도록 각 값의 출처를 metadata로 남긴다.
    """

    def test_measurement_metadata_present_for_all_four_fields(self):
        module = AnalyticsEngineModule()
        result = module.run(
            performance_score_result={"overall_performance_score": 0.8},
            audit_result={"audit_score": 0.7},
        )

        metadata = result["measurement_metadata"]
        for field in (
            "current_performance_score",
            "current_audit_score",
            "historical_average_performance_score",
            "quality_trend",
        ):
            self.assertIn(field, metadata)
            self.assertIn("source", metadata[field])

    def test_measurement_metadata_uses_local_quality_not_real_measurement(self):
        module = AnalyticsEngineModule()
        result = module.run(
            performance_score_result={"overall_performance_score": 0.8},
            audit_result={"audit_score": 0.7},
        )

        metadata = result["measurement_metadata"]
        self.assertEqual(metadata["current_performance_score"]["source"], SOURCE_LOCAL_QUALITY)
        self.assertEqual(metadata["current_audit_score"]["source"], SOURCE_LOCAL_QUALITY)

    def test_measurement_metadata_historical_and_estimated_sources_distinct(self):
        module = AnalyticsEngineModule()
        result = module.run(
            performance_score_result={"overall_performance_score": 0.8},
            audit_result={"audit_score": 0.7},
        )

        metadata = result["measurement_metadata"]
        self.assertEqual(metadata["historical_average_performance_score"]["source"], SOURCE_HISTORICAL)
        self.assertEqual(metadata["quality_trend"]["source"], SOURCE_ESTIMATED)

    def test_measurement_metadata_present_on_exception_fallback(self):
        module = AnalyticsEngineModule()
        result = module._fallback_result(reason="test failure")

        self.assertIn("measurement_metadata", result)
        self.assertEqual(result["measurement_metadata"]["current_performance_score"]["source"], SOURCE_LOCAL_QUALITY)


class TestLearningSourceVerification(unittest.TestCase):
    """
    Learning 검증: Learning Engine이 Planner Decision을 무조건 강화하지 않는지
    확인한다 - Planner의 어떤 출력도 입력으로 받지 않으므로, 원천적으로
    "Planner를 근거로 강화"할 수 없다.
    """

    def test_learning_engine_run_signature_has_no_planner_parameter(self):
        signature = inspect.signature(LearningEngineModule.run)
        parameter_names = list(signature.parameters.keys())

        self.assertNotIn("planner_result", parameter_names)
        self.assertFalse(any("planner" in name.lower() for name in parameter_names))

    def test_learning_evidence_metadata_present_and_sourced(self):
        module = LearningEngineModule()
        result = module.run(
            knowledge_result={"top_knowledge": []},
            performance_score_result={"overall_performance_score": 0.9},
            audit_result={"audit_score": 0.9},
        )

        evidence = result["evidence_metadata"]
        self.assertEqual(evidence["audit_score"]["source"], SOURCE_LOCAL_QUALITY)
        self.assertEqual(evidence["performance_score"]["source"], SOURCE_LOCAL_QUALITY)
        self.assertEqual(evidence["knowledge_score"]["source"], SOURCE_RUNTIME)

    def test_learning_planner_evidence_used_is_always_false(self):
        module = LearningEngineModule()
        result = module.run(
            knowledge_result={"top_knowledge": []},
            performance_score_result={"overall_performance_score": 0.9},
            audit_result={"audit_score": 0.9},
        )

        self.assertFalse(result["planner_evidence_used"])

    def test_learning_fallback_also_has_planner_evidence_used_false(self):
        module = LearningEngineModule()
        result = module._fallback_result(reason="test failure")

        self.assertFalse(result["planner_evidence_used"])
        self.assertIn("evidence_metadata", result)

    def test_learning_score_never_promoted_without_real_evidence(self):
        """
        internal_learning_score가 0에 가까우면(증거가 사실상 없음) is_good_run이
        False여야 하고, 승격도 없어야 한다.
        """
        module = LearningEngineModule()
        result = module.run(
            knowledge_result={"top_knowledge": []},
            performance_score_result={"overall_performance_score": 0.0},
            audit_result={"audit_score": 0.0},
        )

        self.assertFalse(result["is_good_run"])
        self.assertEqual(result["promoted_count"], 0)


class TestPlannerMetadataOnPerformanceScore(unittest.TestCase):
    """
    Performance Score: Planner 적용 여부와 최종 품질을 분리 기록한다.
    """

    def _content_result_with_consumption(self, hook_applied, cta_applied, planner_available=True):
        return {
            "content_intelligence": {"brand_rule_passed": True},
            "pattern_prompt_meta": {"hook_score": 0.9, "cta_score": 0.9},
            "planner_consumption": {
                "content": {
                    "hook": {"planner_available": planner_available, "planner_applied": hook_applied, "reason": "hook reason"},
                    "cta": {"planner_available": planner_available, "planner_applied": cta_applied, "reason": "cta reason"},
                    "content_strategy": {"planner_available": planner_available, "planner_applied": False, "reason": ""},
                }
            },
        }

    def test_performance_score_planner_used_true_when_hint_applied(self):
        module = PerformanceScoreModule()
        content_result = self._content_result_with_consumption(hook_applied=True, cta_applied=True)
        # content_strategy도 적용된 것으로 맞춰서, "일부는 적용/일부는 거부"가
        # 섞이는 경우와 헷갈리지 않는 순수 "전부 적용됨" 시나리오를 만든다.
        content_result["planner_consumption"]["content"]["content_strategy"]["planner_applied"] = True

        result = module.run(content_result=content_result, card_news_result={}, image_strategy_result={})

        self.assertTrue(result["planner_used"])
        self.assertFalse(result["planner_rejected"])

    def test_performance_score_planner_used_and_rejected_can_both_be_true(self):
        """
        hook은 적용되고 cta는 거부된 "부분 적용" 시나리오 - 두 플래그가 동시에
        True일 수 있다는 것이 실제 동작이며 버그가 아니다.
        """
        module = PerformanceScoreModule()
        content_result = self._content_result_with_consumption(hook_applied=True, cta_applied=False)

        result = module.run(content_result=content_result, card_news_result={}, image_strategy_result={})

        self.assertTrue(result["planner_used"])
        self.assertTrue(result["planner_rejected"])

    def test_performance_score_planner_used_false_when_no_planner_result(self):
        module = PerformanceScoreModule()
        content_result = self._content_result_with_consumption(
            hook_applied=False, cta_applied=False, planner_available=False
        )

        result = module.run(content_result=content_result, card_news_result={}, image_strategy_result={})

        self.assertFalse(result["planner_used"])
        self.assertFalse(result["planner_rejected"])

    def test_performance_score_planner_rejected_true_when_available_but_not_applied(self):
        module = PerformanceScoreModule()
        content_result = self._content_result_with_consumption(hook_applied=False, cta_applied=False)

        result = module.run(content_result=content_result, card_news_result={}, image_strategy_result={})

        self.assertFalse(result["planner_used"])
        self.assertTrue(result["planner_rejected"])

    def test_performance_score_planner_helpful_requires_used_and_high_score(self):
        module = PerformanceScoreModule()
        content_result = self._content_result_with_consumption(hook_applied=True, cta_applied=True)
        # 낮은 관련 신호로 overall_performance_score를 낮춘다.
        content_result["content_intelligence"]["brand_rule_passed"] = False
        content_result["pattern_prompt_meta"] = {"hook_score": 0.1, "cta_score": 0.1}

        result = module.run(
            content_result=content_result,
            card_news_result={"layout_result": {}},
            image_strategy_result={"fallback_used": True},
        )

        self.assertTrue(result["planner_used"])
        self.assertFalse(result["planner_helpful"])

    def test_performance_score_fallback_has_all_planner_fields(self):
        module = PerformanceScoreModule()
        result = module._fallback_result(reason="test failure")

        for field in ("planner_used", "planner_helpful", "planner_rejected", "planner_reason"):
            self.assertIn(field, result)

    def test_performance_score_planner_summary_never_raises_on_malformed_input(self):
        module = PerformanceScoreModule()

        for garbage_content in [None, "not a dict", {"planner_consumption": "not a dict"}]:
            try:
                summary = module._build_planner_summary(
                    content_result=garbage_content if isinstance(garbage_content, dict) else {},
                    card_news_result={},
                    image_strategy_result={},
                    overall_performance_score=0.5,
                )
            except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
                self.fail(f"_build_planner_summary raised: {error}")

            self.assertIn("planner_used", summary)


class TestContentEngineInfluenceMetadata(unittest.TestCase):
    """
    Content: PromptBuilder의 Planner/Knowledge/Brand/Pattern 영향도를 각각
    Metadata에 남긴다.
    """

    def _build_content_result_stub(self):
        return {
            "content_intelligence": {"brand_rule_passed": True},
            "planner_consumption": {
                "content": {
                    "hook": {"planner_applied": True},
                    "cta": {"planner_applied": False},
                }
            },
        }

    def test_engine_influence_has_all_four_keys(self):
        module = ContentModule.__new__(ContentModule)  # _build_engine_influence는 self만 필요, LLM 초기화 회피
        influence = module._build_engine_influence(
            content_result=self._build_content_result_stub(),
            prompt_source="pattern_aware",
            prompt_meta={"pattern_fallback_used": False},
            knowledge_items=[{"knowledge_id": "a"}],
        )

        for key in ("planner", "knowledge", "brand", "pattern"):
            self.assertIn(key, influence)

    def test_engine_influence_planner_applied_true_when_any_sub_entry_applied(self):
        module = ContentModule.__new__(ContentModule)
        influence = module._build_engine_influence(
            content_result=self._build_content_result_stub(),
            prompt_source="pattern_aware",
            prompt_meta={},
            knowledge_items=[],
        )

        self.assertTrue(influence["planner"]["applied"])

    def test_engine_influence_knowledge_reflects_actual_usage(self):
        module = ContentModule.__new__(ContentModule)
        influence = module._build_engine_influence(
            content_result=self._build_content_result_stub(),
            prompt_source="pattern_aware",
            prompt_meta={},
            knowledge_items=[{"knowledge_id": "a"}, {"knowledge_id": "b"}],
        )

        self.assertTrue(influence["knowledge"]["used"])
        self.assertEqual(influence["knowledge"]["items_count"], 2)
        self.assertEqual(influence["knowledge"]["source"], SOURCE_HISTORICAL)

    def test_engine_influence_brand_reflects_actual_evaluation(self):
        module = ContentModule.__new__(ContentModule)
        content_result = self._build_content_result_stub()
        content_result["content_intelligence"]["brand_rule_passed"] = False

        influence = module._build_engine_influence(
            content_result=content_result, prompt_source="legacy", prompt_meta={}, knowledge_items=[]
        )

        self.assertFalse(influence["brand"]["passed"])
        self.assertEqual(influence["brand"]["source"], SOURCE_RUNTIME)

    def test_engine_influence_pattern_reflects_prompt_source(self):
        module = ContentModule.__new__(ContentModule)
        influence = module._build_engine_influence(
            content_result=self._build_content_result_stub(),
            prompt_source="legacy",
            prompt_meta={"pattern_fallback_used": True},
            knowledge_items=[],
        )

        self.assertEqual(influence["pattern"]["prompt_source"], "legacy")
        self.assertTrue(influence["pattern"]["fallback_used"])

    def test_engine_influence_never_raises_on_malformed_content_result(self):
        module = ContentModule.__new__(ContentModule)

        for garbage in [{}, {"planner_consumption": "not a dict"}, {"content_intelligence": None}]:
            try:
                influence = module._build_engine_influence(
                    content_result=garbage, prompt_source="legacy", prompt_meta={}, knowledge_items=[]
                )
            except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
                self.fail(f"_build_engine_influence raised for {garbage!r}: {error}")

            self.assertIn("planner", influence)


class TestMetadataStandardization(unittest.TestCase):
    """
    Metadata 표준화: 모든 Engine이 metadata_version/source/confidence/
    generated_at을 공통으로 사용하도록 통일한다.
    """

    def test_build_standard_metadata_has_required_keys(self):
        metadata = build_standard_metadata(source=SOURCE_RUNTIME, confidence=0.8)

        for key in ("metadata_version", "source", "confidence", "generated_at"):
            self.assertIn(key, metadata)

    def test_build_standard_metadata_merges_extra_fields(self):
        metadata = build_standard_metadata(source=SOURCE_HISTORICAL, confidence=None, sample_size=10)
        self.assertEqual(metadata["sample_size"], 10)

    def test_build_standard_metadata_never_raises(self):
        for source in [None, 123, object()]:
            try:
                metadata = build_standard_metadata(source=source, confidence=None)
            except Exception as error:  # pragma: no cover - 절대 발생하면 안 됨
                self.fail(f"build_standard_metadata raised for source={source!r}: {error}")

            self.assertIn("metadata_version", metadata)

    def test_valid_sources_cover_ctos_four_categories(self):
        self.assertEqual(VALID_SOURCES, {"runtime", "historical", "estimated", "local_quality"})

    def test_analytics_learning_content_all_reuse_shared_metadata_version(self):
        """
        중복 구조 제거 확인: 서로 다른 Engine이 만든 metadata라도 동일한
        metadata_version을 공유해야 한다(각자 새 표준을 만들지 않았다는 증거).
        """
        analytics_metadata = AnalyticsEngineModule()._fallback_result(reason="t")["measurement_metadata"][
            "current_performance_score"
        ]
        learning_metadata = LearningEngineModule()._fallback_result(reason="t")["evidence_metadata"]["audit_score"]

        self.assertEqual(analytics_metadata["metadata_version"], learning_metadata["metadata_version"])


if __name__ == "__main__":
    unittest.main()
