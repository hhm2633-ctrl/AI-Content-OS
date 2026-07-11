"""
Instagram Intelligence Phase - 최종 검증 위험 테스트.

테스트 개수 목표는 없다. 아래 6개 위험만 최소 테스트로 확인한다:

A. 같은 content_id 반복 처리 시 content_performance_history 무한 중복 누적 방지
B. 같은 실행 결과 반복 처리 시 Knowledge confidence 중복 적용 방지
C. confidence는 항상 0.0~1.0 범위 유지
D. 독립 관찰 5회 미만이면 Brand DNA Feedback 미적용
E. 내부 quality proxy와 실제 external performance가 명확히 분리
F. 기존 Pattern/Hook/CTA 선택값은 변경되지 않고 confidence만 보정됨
"""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.brand_dna_engine.brand_dna_engine_module import BrandDNAEngineModule
from modules.competitor_learning.competitor_learning_storage import CompetitorLearningStorage
from modules.learning_engine.content_performance_history import ContentPerformanceHistory
from modules.learning_engine.learning_engine_module import LearningEngineModule
from modules.pattern_engine.pattern_engine_module import PatternEngineModule


def _score_entry(entry_type, value, score=0.9, sample_size=10):
    return {
        "knowledge_id": f"competitor_learning_{entry_type}_{value}",
        "type": entry_type,
        "value": value,
        "score": {"overall_score": score},
        "sample_size": sample_size,
    }


class _FakeCompetitorLearningInterface:
    def __init__(self, hooks=None, ctas=None, patterns=None):
        self._hooks = hooks or []
        self._ctas = ctas or []
        self._patterns = patterns or []

    def is_available(self):
        return True

    def get_top_hooks(self, limit=5):
        return self._hooks[:limit]

    def get_top_ctas(self, limit=5):
        return self._ctas[:limit]

    def get_top_patterns(self, limit=5):
        return self._patterns[:limit]


class _FakeLearningInterface:
    def __init__(self, hooks=None, ctas=None, patterns=None):
        self._by_type = {"hook": hooks or [], "cta": ctas or [], "pattern": patterns or []}

    def get_top_memory(self, knowledge_type=None, limit=5):
        return self._by_type.get(knowledge_type, [])[:limit]


class _FakeBrandDNAInterface:
    def __init__(self, dna):
        self._dna = dna

    def get_dna(self):
        return self._dna


# ---- Risk A: content_id 반복 처리 시 무한 중복 누적 방지 ----


class TestRiskA_ContentPerformanceHistoryDedup(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="risk_a_test_")
        self.history = ContentPerformanceHistory(history_path=Path(self.tmp_dir) / "history.json")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_record_once_skips_duplicate_content_id(self):
        entry = {"content_id": "abc123", "quality_score": 0.8}

        first = self.history.record_once(dict(entry))
        second = self.history.record_once(dict(entry))
        third = self.history.record_once(dict(entry))

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertFalse(third)
        self.assertEqual(len(self.history.load_all()), 1)

    def test_record_once_allows_different_content_id(self):
        self.history.record_once({"content_id": "a"})
        self.history.record_once({"content_id": "b"})
        self.assertEqual(len(self.history.load_all()), 2)

    def test_record_once_rejects_empty_content_id(self):
        result = self.history.record_once({"content_id": ""})
        self.assertFalse(result)
        self.assertEqual(self.history.load_all(), [])

    def test_build_content_id_deterministic_not_wall_clock_salted(self):
        """
        회귀 방지: content_id는 title/caption처럼 콘텐츠 자체의 값으로만
        구성되어야 한다 - datetime.now()가 섞이면 같은 콘텐츠도 매번 다른
        id가 나와 dedup이 무력화된다.
        """
        id1 = self.history.build_content_id("동일 제목", "동일 캡션")
        id2 = self.history.build_content_id("동일 제목", "동일 캡션")
        self.assertEqual(id1, id2)

    def test_build_content_id_differs_for_different_content(self):
        id1 = self.history.build_content_id("제목 A", "캡션 A")
        id2 = self.history.build_content_id("제목 B", "캡션 B")
        self.assertNotEqual(id1, id2)


# ---- Risk B: 같은 실행 결과 반복 처리 시 Knowledge confidence 중복 적용 방지 ----


class TestRiskB_KnowledgeFeedbackDedup(unittest.TestCase):
    def setUp(self):
        self.module = LearningEngineModule()

    def test_skips_confidence_adjustment_when_entry_already_recorded(self):
        result = self.module._apply_knowledge_feedback(
            {"deduplicated": True, "hook": "attention", "cta": "save", "pattern": "funnel"},
            is_good_run=True,
        )
        self.assertEqual(result["adjusted_count"], 0)
        self.assertEqual(result["delta_applied"], 0.0)
        self.assertIn("skipped_reason", result)

    def test_applies_confidence_adjustment_only_for_new_entry(self):
        with patch.object(
            self.module.competitor_learning_storage,
            "adjust_entry_confidence",
            return_value={"score": {"confidence": 0.55}},
        ) as mock_adjust:
            result = self.module._apply_knowledge_feedback(
                {"deduplicated": False, "hook": "attention", "cta": "save", "pattern": "funnel"},
                is_good_run=True,
            )

        self.assertEqual(result["adjusted_count"], 3)
        self.assertEqual(mock_adjust.call_count, 3)


# ---- Risk C: confidence는 항상 0.0~1.0 범위 유지 ----


class TestRiskC_ConfidenceBounds(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="risk_c_test_")
        self.storage = CompetitorLearningStorage(
            knowledge_dir=Path(self.tmp_dir) / "knowledge",
            dashboard_dir=Path(self.tmp_dir) / "dashboard",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _seed(self, confidence):
        self.storage.save_knowledge_database(
            [{
                "knowledge_id": "k1", "type": "hook", "value": "attention",
                "score": {"share": 0.5, "confidence": confidence, "engagement_factor": 0.1, "overall_score": 0.6},
            }],
            {},
        )

    def test_confidence_never_exceeds_one_with_repeated_positive_adjustments(self):
        self._seed(0.97)
        entry = None
        for _ in range(20):
            entry = self.storage.adjust_entry_confidence("k1", 0.05)
        self.assertLessEqual(entry["score"]["confidence"], 1.0)
        self.assertGreaterEqual(entry["score"]["overall_score"], 0.0)
        self.assertLessEqual(entry["score"]["overall_score"], 1.0)

    def test_confidence_never_below_zero_with_repeated_negative_adjustments(self):
        self._seed(0.03)
        entry = None
        for _ in range(20):
            entry = self.storage.adjust_entry_confidence("k1", -0.05)
        self.assertGreaterEqual(entry["score"]["confidence"], 0.0)
        self.assertGreaterEqual(entry["score"]["overall_score"], 0.0)

    def test_pattern_engine_cumulative_confidence_boost_capped_at_one(self):
        module = PatternEngineModule()
        module.knowledge_interface = type("F", (), {"get_pattern_knowledge": lambda self, limit=3: [], "get_layout_knowledge": lambda self, limit=3: []})()
        module.competitor_learning_interface = _FakeCompetitorLearningInterface(
            hooks=[_score_entry("hook", "attention")],
            ctas=[_score_entry("cta", "save")],
            patterns=[_score_entry("pattern", "tutorial")],
        )
        module.brand_dna_interface = _FakeBrandDNAInterface(
            {"total_observations": 10, "planner_influenced_observations": 0,
             "dominant_hook_type": "attention", "dominant_cta_type": "save"}
        )
        module.learning_interface = _FakeLearningInterface(
            hooks=[_score_entry("hook", "attention")],
            ctas=[_score_entry("cta", "save")],
            patterns=[_score_entry("pattern", "tutorial")],
        )

        result = {
            "topic_intelligence": {"confidence_score": 0.99},
            "pattern_plan": {"pattern_type": "tutorial", "hook_type": "attention", "cta_type": "save", "layout_type": "bold_ai"},
        }
        result = module._apply_knowledge_consumption(result)
        result = module._apply_competitor_learning_consumption(result)
        result = module._apply_brand_dna_consumption(result)
        result = module._apply_learning_consumption(result)

        self.assertLessEqual(result["topic_intelligence"]["confidence_score"], 1.0)


# ---- Risk D: 독립 관찰 5회 미만이면 Brand DNA Feedback 미적용 ----


class TestRiskD_IndependentObservationGate(unittest.TestCase):
    def test_pattern_engine_brand_dna_blocked_below_threshold(self):
        module = PatternEngineModule()
        module.brand_dna_interface = _FakeBrandDNAInterface(
            {"total_observations": 4, "planner_influenced_observations": 0,
             "dominant_hook_type": "attention", "dominant_cta_type": "save"}
        )
        result = module._apply_brand_dna_consumption({
            "topic_intelligence": {"confidence_score": 0.5},
            "pattern_plan": {"hook_type": "attention", "cta_type": "save"},
        })
        self.assertFalse(result["brand_dna_used"])
        self.assertEqual(result["topic_intelligence"]["confidence_score"], 0.5)

    def test_pattern_engine_brand_dna_allowed_at_threshold(self):
        module = PatternEngineModule()
        module.brand_dna_interface = _FakeBrandDNAInterface(
            {"total_observations": 5, "planner_influenced_observations": 0,
             "dominant_hook_type": "attention", "dominant_cta_type": "save"}
        )
        result = module._apply_brand_dna_consumption({
            "topic_intelligence": {"confidence_score": 0.5},
            "pattern_plan": {"hook_type": "attention", "cta_type": "save"},
        })
        self.assertTrue(result["brand_dna_used"])

    def test_brand_dna_learning_feedback_blocked_below_threshold(self):
        module = BrandDNAEngineModule()
        reference = module._build_learning_feedback_reference(
            {"total_observations": 4, "planner_influenced_observations": 0}
        )
        self.assertFalse(reference["available"])

    def test_brand_dna_learning_feedback_allowed_at_threshold(self):
        module = BrandDNAEngineModule()
        with patch.object(
            module.learning_interface, "get_statistics",
            return_value={"total_runs": 10, "total_good_runs": 6},
        ):
            reference = module._build_learning_feedback_reference(
                {"total_observations": 5, "planner_influenced_observations": 0}
            )
        self.assertTrue(reference["available"])
        self.assertEqual(reference["recent_good_run_ratio"], 0.6)

    def test_independent_observations_excludes_planner_influenced(self):
        # total=6이지만 planner_influenced=2라 독립 관찰은 4 -> 기준(5) 미달.
        module = PatternEngineModule()
        module.brand_dna_interface = _FakeBrandDNAInterface(
            {"total_observations": 6, "planner_influenced_observations": 2,
             "dominant_hook_type": "attention", "dominant_cta_type": "save"}
        )
        result = module._apply_brand_dna_consumption({
            "topic_intelligence": {"confidence_score": 0.5},
            "pattern_plan": {"hook_type": "attention", "cta_type": "save"},
        })
        self.assertFalse(result["brand_dna_used"])


# ---- Risk E: 내부 quality proxy와 실제 external performance 분리 ----


class TestRiskE_InternalQualityProxyLabeling(unittest.TestCase):
    def test_metadata_constant_values(self):
        metadata = LearningEngineModule.INTERNAL_QUALITY_PROXY_METADATA
        self.assertEqual(metadata["performance_source"], "internal_quality_proxy")
        self.assertFalse(metadata["external_metrics_used"])
        self.assertFalse(metadata["external_metrics_available"])
        self.assertEqual(metadata["learning_scope"], "pre_publish_internal_feedback")

    def test_fallback_result_includes_proxy_metadata(self):
        module = LearningEngineModule()
        result = module._fallback_result(reason="test")
        self.assertEqual(result["performance_source"], "internal_quality_proxy")
        self.assertFalse(result["external_metrics_used"])
        self.assertFalse(result["external_metrics_available"])
        self.assertEqual(result["learning_scope"], "pre_publish_internal_feedback")

    def test_fallback_result_performance_history_entry_includes_proxy_metadata(self):
        """Codex 검수 지적 사항: _fallback_result()의 performance_history_entry가
        빈 dict({})라 top-level에는 있는 라벨이 이 하위 필드에는 빠져 있었다."""
        module = LearningEngineModule()
        result = module._fallback_result(reason="test")
        entry_metadata = result["performance_history_entry"]
        self.assertEqual(entry_metadata["performance_source"], "internal_quality_proxy")
        self.assertFalse(entry_metadata["external_metrics_used"])
        self.assertFalse(entry_metadata["external_metrics_available"])
        self.assertEqual(entry_metadata["learning_scope"], "pre_publish_internal_feedback")

    def test_dashboard_merge_includes_internal_quality_feedback_notice(self):
        tmp_dir = tempfile.mkdtemp(prefix="risk_e_test_")
        try:
            module = LearningEngineModule()
            module.dashboard_storage = CompetitorLearningStorage(
                knowledge_dir=Path(tmp_dir) / "knowledge", dashboard_dir=Path(tmp_dir) / "dashboard"
            )
            module._merge_dashboard(
                performance_analysis={"top_performing_pattern": "tutorial", "weakest_pattern": "story"},
                learning_delta={"previous": 0.5, "current": 0.6, "delta": 0.1},
                knowledge_feedback={"adjusted_count": 1, "delta_applied": 0.05},
            )
            report = module.dashboard_storage.load_dashboard()
            notice = report.get("internal_quality_feedback_metadata", {})
            self.assertEqual(notice.get("performance_source"), "internal_quality_proxy")
            self.assertFalse(notice.get("external_metrics_used"))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


# ---- Risk F: 기존 Pattern/Hook/CTA 선택값은 변경되지 않고 confidence만 보정 ----


class TestRiskF_SelectionValuesUnchanged(unittest.TestCase):
    def setUp(self):
        self.pattern_plan = {
            "pattern_type": "tutorial", "hook_type": "attention",
            "cta_type": "save", "layout_type": "bold_ai",
        }

    def test_competitor_learning_consumption_does_not_mutate_pattern_plan(self):
        module = PatternEngineModule()
        module.competitor_learning_interface = _FakeCompetitorLearningInterface(
            hooks=[_score_entry("hook", "attention")],
            ctas=[_score_entry("cta", "save")],
            patterns=[_score_entry("pattern", "tutorial")],
        )
        result = {"topic_intelligence": {"confidence_score": 0.5}, "pattern_plan": dict(self.pattern_plan)}
        updated = module._apply_competitor_learning_consumption(result)
        self.assertEqual(updated["pattern_plan"], self.pattern_plan)

    def test_brand_dna_consumption_does_not_mutate_pattern_plan(self):
        module = PatternEngineModule()
        module.brand_dna_interface = _FakeBrandDNAInterface(
            {"total_observations": 10, "planner_influenced_observations": 0,
             "dominant_hook_type": "attention", "dominant_cta_type": "save"}
        )
        result = {"topic_intelligence": {"confidence_score": 0.5}, "pattern_plan": dict(self.pattern_plan)}
        updated = module._apply_brand_dna_consumption(result)
        self.assertEqual(updated["pattern_plan"], self.pattern_plan)

    def test_learning_consumption_does_not_mutate_pattern_plan(self):
        module = PatternEngineModule()
        module.learning_interface = _FakeLearningInterface(
            hooks=[_score_entry("hook", "attention")],
            ctas=[_score_entry("cta", "save")],
            patterns=[_score_entry("pattern", "tutorial")],
        )
        result = {"topic_intelligence": {"confidence_score": 0.5}, "pattern_plan": dict(self.pattern_plan)}
        updated = module._apply_learning_consumption(result)
        self.assertEqual(updated["pattern_plan"], self.pattern_plan)

    def test_knowledge_feedback_never_creates_new_knowledge_entry(self):
        tmp_dir = tempfile.mkdtemp(prefix="risk_f_test_")
        try:
            storage = CompetitorLearningStorage(
                knowledge_dir=Path(tmp_dir) / "knowledge", dashboard_dir=Path(tmp_dir) / "dashboard"
            )
            result = storage.adjust_entry_confidence("nonexistent_id", 0.05)
            self.assertIsNone(result)
            self.assertEqual(storage.load_knowledge_database()["entries"], [])
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
