import unittest
from unittest.mock import patch

from modules.brand_dna_engine.brand_dna_engine_module import BrandDNAEngineModule
from modules.content.content_module import ContentModule
from modules.content.content_prompt_builder import ContentPromptBuilder
from modules.pattern_engine.pattern_engine_module import PatternEngineModule


def _score_entry(entry_type, value, score=0.9, sample_size=10):
    return {
        "knowledge_id": f"competitor_learning_{entry_type}_{value}",
        "type": entry_type,
        "value": value,
        "score": {"overall_score": score},
        "sample_size": sample_size,
    }


class _FakeCompetitorInterface:
    def __init__(self, available=True, hooks=None, ctas=None, patterns=None, layouts=None, accounts=None):
        self._available = available
        self._hooks = hooks or []
        self._ctas = ctas or []
        self._patterns = patterns or []
        self._layouts = layouts or []
        self._accounts = accounts or {}

    def is_available(self):
        return self._available

    def get_top_hooks(self, limit=5):
        return self._hooks[:limit]

    def get_top_ctas(self, limit=5):
        return self._ctas[:limit]

    def get_top_patterns(self, limit=5):
        return self._patterns[:limit]

    def get_top_layouts(self, limit=5):
        return self._layouts[:limit]

    def get_competitor_statistics(self):
        return {"accounts": self._accounts, "account_count": len(self._accounts)}

    def get_knowledge_database(self):
        return {"new_count": 0, "total_count": 0}


class _FakeLLMClient:
    def generate_text(self, system_prompt, user_prompt):
        import json
        return json.dumps({
            "title": "테스트 카드뉴스",
            "slides": [
                {"page": 1, "role": "hook", "headline": "훅 제목", "body": "훅 본문입니다."},
                {"page": 2, "role": "problem", "headline": "문제 제목", "body": "문제 본문입니다."},
                {"page": 3, "role": "solution", "headline": "해결 제목", "body": "해결 본문입니다."},
                {"page": 4, "role": "cta", "headline": "CTA 제목", "body": "CTA 본문입니다."},
            ],
            "caption": "캡션",
            "hashtags": ["#a", "#b", "#c"],
            "status": "content_created",
        })


class TestPatternEngineCompetitorLearningWiring(unittest.TestCase):
    def setUp(self):
        self.module = PatternEngineModule()

    def test_competitor_learning_used_false_when_db_unavailable(self):
        self.module.competitor_learning_interface = _FakeCompetitorInterface(available=False)
        result = self.module._apply_competitor_learning_consumption({
            "topic_intelligence": {"confidence_score": 0.5},
            "pattern_plan": {"pattern_type": "tutorial", "hook_type": "pain_point", "cta_type": "follow"},
        })
        self.assertFalse(result["competitor_learning_used"])

    def test_boosts_confidence_when_pattern_matches(self):
        self.module.competitor_learning_interface = _FakeCompetitorInterface(
            patterns=[_score_entry("pattern", "tutorial")]
        )
        result = self.module._apply_competitor_learning_consumption({
            "topic_intelligence": {"confidence_score": 0.5},
            "pattern_plan": {"pattern_type": "tutorial", "hook_type": "pain_point", "cta_type": "follow"},
        })
        self.assertTrue(result["competitor_learning_used"])
        self.assertEqual(result["topic_intelligence"]["confidence_score"], 0.53)

    def test_confidence_boost_is_capped_at_one(self):
        self.module.competitor_learning_interface = _FakeCompetitorInterface(
            patterns=[_score_entry("pattern", "tutorial")]
        )
        result = self.module._apply_competitor_learning_consumption({
            "topic_intelligence": {"confidence_score": 0.99},
            "pattern_plan": {"pattern_type": "tutorial", "hook_type": "pain_point", "cta_type": "follow"},
        })
        self.assertLessEqual(result["topic_intelligence"]["confidence_score"], 1.0)

    def test_no_boost_when_nothing_matches(self):
        self.module.competitor_learning_interface = _FakeCompetitorInterface(
            patterns=[_score_entry("pattern", "story")]
        )
        result = self.module._apply_competitor_learning_consumption({
            "topic_intelligence": {"confidence_score": 0.5},
            "pattern_plan": {"pattern_type": "tutorial", "hook_type": "pain_point", "cta_type": "follow"},
        })
        self.assertFalse(result["competitor_learning_used"])
        self.assertEqual(result["topic_intelligence"]["confidence_score"], 0.5)

    def test_does_not_touch_layout_matching(self):
        # layout_type을 일치시켜도 (다른 값 체계이므로) confidence_score가 바뀌면 안 된다.
        self.module.competitor_learning_interface = _FakeCompetitorInterface(
            layouts=[_score_entry("layout", "bold_ai")]
        )
        result = self.module._apply_competitor_learning_consumption({
            "topic_intelligence": {"confidence_score": 0.5},
            "pattern_plan": {"pattern_type": "tutorial", "hook_type": "pain_point", "cta_type": "follow", "layout_type": "bold_ai"},
        })
        self.assertEqual(result["topic_intelligence"]["confidence_score"], 0.5)
        self.assertFalse(result["competitor_learning_used"])

    def test_never_raises_when_interface_throws(self):
        class RaisingInterface:
            def is_available(self):
                raise RuntimeError("boom")

        self.module.competitor_learning_interface = RaisingInterface()
        result = self.module._apply_competitor_learning_consumption({
            "topic_intelligence": {"confidence_score": 0.5},
            "pattern_plan": {"pattern_type": "tutorial"},
        })
        self.assertFalse(result["competitor_learning_used"])

    def test_pattern_selector_itself_is_never_overridden(self):
        # 이 메서드는 pattern_type을 바꾸지 않는다 - confidence_score/메타데이터만 조정한다.
        self.module.competitor_learning_interface = _FakeCompetitorInterface(
            patterns=[_score_entry("pattern", "tutorial")]
        )
        pattern_plan = {"pattern_type": "tutorial", "hook_type": "pain_point", "cta_type": "follow"}
        result = self.module._apply_competitor_learning_consumption({
            "topic_intelligence": {"confidence_score": 0.5},
            "pattern_plan": pattern_plan,
        })
        self.assertEqual(result["pattern_plan"]["pattern_type"], "tutorial")

    def test_run_never_raises_end_to_end_without_selected_topic(self):
        self.module.competitor_learning_interface = _FakeCompetitorInterface(available=False)
        result = self.module.run(selected_topic={}, trend_result={})
        self.assertIn("competitor_learning_used", result)


class TestContentPromptBuilderCompetitorLearningWiring(unittest.TestCase):
    def setUp(self):
        self.builder = ContentPromptBuilder()
        self.research_result = {
            "keyword": "AI 자동화",
            "pattern_plan": {
                "pattern_type": "tutorial",
                "hook_type": "pain_point",
                "cta_type": "follow",
                "layout_type": "bold_ai",
            },
            "topic_intelligence": {"blocked": False, "confidence_score": 0.7, "keywords": []},
        }

    def test_prioritizes_competitor_hint_over_planner(self):
        self.builder.competitor_learning_interface = _FakeCompetitorInterface(
            hooks=[_score_entry("hook", "authority")],
            ctas=[_score_entry("cta", "dm")],
        )
        planner_result = {
            "status": "planner_decided",
            "schema_valid": True,
            "planner_confidence": 0.9,
            "selected_hook_strategy": "contrarian",
            "selected_cta_strategy": "comment",
        }
        out = self.builder.build(self.research_result, planner_result)
        self.assertEqual(out["meta"]["hook_type"], "authority")
        self.assertEqual(out["meta"]["cta_type"], "dm")
        self.assertTrue(out["meta"]["competitor_learning_consumption"]["hook"]["applied"])
        self.assertTrue(out["meta"]["competitor_learning_consumption"]["cta"]["applied"])

    def test_falls_back_to_planner_when_no_competitor_hint(self):
        self.builder.competitor_learning_interface = _FakeCompetitorInterface(available=False)
        planner_result = {
            "status": "planner_decided",
            "schema_valid": True,
            "planner_confidence": 0.9,
            "selected_hook_strategy": "contrarian",
            "selected_cta_strategy": "comment",
        }
        out = self.builder.build(self.research_result, planner_result)
        self.assertEqual(out["meta"]["hook_type"], "contrarian")
        self.assertEqual(out["meta"]["cta_type"], "comment")
        self.assertFalse(out["meta"]["competitor_learning_consumption"]["hook"]["applied"])

    def test_falls_back_to_engine_default_when_neither_available(self):
        self.builder.competitor_learning_interface = _FakeCompetitorInterface(available=False)
        out = self.builder.build(self.research_result, planner_result=None)
        self.assertEqual(out["meta"]["hook_type"], "beginner")
        self.assertEqual(out["meta"]["cta_type"], "follow")

    def test_respects_blocked_flag(self):
        self.builder.competitor_learning_interface = _FakeCompetitorInterface(
            hooks=[_score_entry("hook", "authority")],
        )
        research_result = dict(self.research_result)
        research_result["topic_intelligence"] = {"blocked": True, "confidence_score": 0.7, "keywords": []}
        out = self.builder.build(research_result, planner_result=None)
        self.assertFalse(out["meta"]["competitor_learning_consumption"]["hook"]["applied"])

    def test_respects_min_sample_size_threshold(self):
        self.builder.competitor_learning_interface = _FakeCompetitorInterface(
            hooks=[_score_entry("hook", "authority", score=0.9, sample_size=1)],
        )
        out = self.builder.build(self.research_result, planner_result=None)
        self.assertFalse(out["meta"]["competitor_learning_consumption"]["hook"]["applied"])

    def test_respects_min_score_threshold(self):
        self.builder.competitor_learning_interface = _FakeCompetitorInterface(
            hooks=[_score_entry("hook", "authority", score=0.1, sample_size=10)],
        )
        out = self.builder.build(self.research_result, planner_result=None)
        self.assertFalse(out["meta"]["competitor_learning_consumption"]["hook"]["applied"])

    def test_invalid_override_value_ignored(self):
        self.builder.competitor_learning_interface = _FakeCompetitorInterface(
            hooks=[_score_entry("hook", "not_a_real_hook_type", score=0.9, sample_size=10)],
        )
        out = self.builder.build(self.research_result, planner_result=None)
        self.assertFalse(out["meta"]["competitor_learning_consumption"]["hook"]["applied"])

    def test_resolve_competitor_hint_never_raises(self):
        result = self.builder._resolve_competitor_hint("not_a_list", blocked=False)
        self.assertIsNone(result)


class TestContentModuleCompetitorLearningWiring(unittest.TestCase):
    def test_surfaces_competitor_learning_fields_when_applied(self):
        module = ContentModule(llm_client=_FakeLLMClient())
        module.prompt_builder.competitor_learning_interface = _FakeCompetitorInterface(
            hooks=[_score_entry("hook", "authority")],
            ctas=[_score_entry("cta", "dm")],
        )
        research_result = {
            "keyword": "AI 자동화",
            "pattern_plan": {"pattern_type": "tutorial", "hook_type": "pain_point", "cta_type": "follow", "layout_type": "bold_ai"},
            "topic_intelligence": {"blocked": False, "confidence_score": 0.7, "keywords": []},
        }
        result = module.run(research_result, planner_result=None)
        self.assertTrue(result["competitor_learning_used"])
        self.assertTrue(len(result["competitor_learning_items"]) > 0)

    def test_legacy_path_records_no_evaluation(self):
        module = ContentModule(llm_client=_FakeLLMClient())
        result = module.run(research_result={}, planner_result=None)
        self.assertFalse(result["competitor_learning_used"])
        self.assertEqual(result["competitor_learning_items"], [])
        self.assertIn("legacy", result["competitor_learning_influence"])


class TestBrandDNACompetitorLearningWiring(unittest.TestCase):
    def setUp(self):
        self.module = BrandDNAEngineModule()

    def test_reference_unavailable_when_db_empty(self):
        self.module.competitor_learning_interface = _FakeCompetitorInterface(available=False)
        reference = self.module._build_competitor_learning_reference()
        self.assertFalse(reference["available"])
        self.assertEqual(reference["account_profiles"], {})

    def test_reference_available_with_account_profiles(self):
        self.module.competitor_learning_interface = _FakeCompetitorInterface(
            available=True, accounts={"brand_a": {"post_count": 3}}
        )
        reference = self.module._build_competitor_learning_reference()
        self.assertTrue(reference["available"])
        self.assertEqual(reference["account_count"], 1)
        self.assertIn("brand_a", reference["account_profiles"])

    def test_reference_never_raises_when_interface_throws(self):
        class RaisingInterface:
            def is_available(self):
                raise RuntimeError("boom")

        self.module.competitor_learning_interface = RaisingInterface()
        reference = self.module._build_competitor_learning_reference()
        self.assertFalse(reference["available"])

    def test_fallback_result_includes_reference_default(self):
        result = self.module._fallback_result(reason="test")
        self.assertIn("competitor_learning_reference", result)
        self.assertFalse(result["competitor_learning_reference"]["available"])

    def test_run_adds_competitor_learning_reference_without_breaking_dominant_fields(self):
        self.module.competitor_learning_interface = _FakeCompetitorInterface(
            available=True, accounts={"brand_a": {"post_count": 3}}
        )
        with patch.object(
            self.module.storage, "update",
            return_value={"dominant_hook_type": "attention", "dominant_cta_type": "save",
                          "dominant_layout_type": "bold_ai", "dominant_color": "#fff", "total_observations": 1},
        ), patch.object(self.module.history, "record"):
            result = self.module.run(
                pattern_result={"pattern_plan": {"hook_type": "attention", "cta_type": "save", "layout_type": "bold_ai"}},
                content_result={"content_intelligence": {"brand_rule_passed": True}},
                card_news_result={"layout_result": {}},
            )

        self.assertEqual(result["dominant_hook_type"], "attention")
        self.assertTrue(result["competitor_learning_reference"]["available"])
        self.assertEqual(result["competitor_learning_reference"]["account_count"], 1)


if __name__ == "__main__":
    unittest.main()
