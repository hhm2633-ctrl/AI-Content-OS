"""Independent coverage for modules/knowledge_engine/knowledge_extractor.py and
knowledge_classifier.py.

Priority-2 gap-fill (continuation): `modules/knowledge_engine/` (an 11-file engine) had zero
dedicated unit tests prior to this file -- only reached incidentally through `KnowledgeModule`
imports in unrelated wiring tests. Both classes here are pure (`config`-only construction, no I/O,
no cross-engine dependency), so they can be tested directly with synthetic pipeline-result dicts.
No existing module or test file is modified.
"""

import unittest

from modules.knowledge_engine.knowledge_classifier import KnowledgeClassifier
from modules.knowledge_engine.knowledge_extractor import KnowledgeExtractor


class KnowledgeExtractorHookCtaTests(unittest.TestCase):
    def setUp(self):
        self.extractor = KnowledgeExtractor()

    def test_extract_returns_only_the_workflow_item_for_empty_context(self):
        # `_extract_workflow` always produces one "clean_run" item regardless
        # of whether any other stage result was supplied -- every other
        # extractor correctly yields nothing for a truly empty context.
        items = self.extractor.extract({})
        self.assertEqual([item["type"] for item in items], ["workflow"])
        self.assertEqual(items[0]["title"], "workflow_run:clean_run")

    def test_extract_handles_non_dict_context(self):
        items = self.extractor.extract("not-a-dict")
        self.assertEqual([item["type"] for item in items], ["workflow"])

    def test_hook_slide_is_extracted(self):
        context = {"content_result": {"slides": [{"role": "hook", "headline": "후킹 문구", "body": "본문"}]}}
        items = self.extractor.extract(context)
        hook_items = [item for item in items if item["type"] == "hook"]
        self.assertEqual(len(hook_items), 1)
        self.assertEqual(hook_items[0]["title"], "후킹 문구")
        self.assertEqual(hook_items[0]["source_module"], "content_module")

    def test_cta_slide_is_extracted(self):
        context = {"content_result": {"slides": [{"role": "cta", "headline": "저장하세요", "body": ""}]}}
        items = self.extractor.extract(context)
        cta_items = [item for item in items if item["type"] == "cta"]
        self.assertEqual(len(cta_items), 1)

    def test_slide_with_neither_headline_nor_body_is_skipped(self):
        context = {"content_result": {"slides": [{"role": "hook", "headline": "", "body": ""}]}}
        items = self.extractor.extract(context)
        self.assertEqual([item for item in items if item["type"] == "hook"], [])

    def test_non_list_slides_does_not_crash(self):
        context = {"content_result": {"slides": "not-a-list"}}
        items = self.extractor.extract(context)
        self.assertEqual([item for item in items if item["type"] in ("hook", "cta")], [])

    def test_hook_content_carries_pattern_plan_field(self):
        context = {
            "content_result": {"slides": [{"role": "hook", "headline": "제목", "body": ""}]},
            "pattern_result": {"pattern_plan": {"hook_type": "question"}},
        }
        items = self.extractor.extract(context)
        hook_item = next(item for item in items if item["type"] == "hook")
        self.assertEqual(hook_item["content"]["hook_type"], "question")


class KnowledgeExtractorOtherTypesTests(unittest.TestCase):
    def setUp(self):
        self.extractor = KnowledgeExtractor()

    def test_pattern_extracted_when_pattern_type_present(self):
        context = {"pattern_result": {"pattern_plan": {"pattern_type": "listicle"}, "topic_intelligence": {"category": "tech"}}}
        items = self.extractor.extract(context)
        pattern_items = [item for item in items if item["type"] == "pattern"]
        self.assertEqual(len(pattern_items), 1)
        self.assertEqual(pattern_items[0]["content"]["category"], "tech")

    def test_pattern_not_extracted_when_missing(self):
        items = self.extractor.extract({"pattern_result": {}})
        self.assertEqual([item for item in items if item["type"] == "pattern"], [])

    def test_layout_extracted_when_layout_type_present(self):
        context = {"card_news_result": {"layout_result": {"layout_type": "notebook", "slide_count": 4}}}
        items = self.extractor.extract(context)
        layout_items = [item for item in items if item["type"] == "layout"]
        self.assertEqual(len(layout_items), 1)

    def test_brand_extracted_when_brand_rule_detail_present(self):
        context = {"content_result": {"content_intelligence": {"brand_rule_passed": True, "details": {"brand_rule": {"note": "ok"}}}}}
        items = self.extractor.extract(context)
        brand_items = [item for item in items if item["type"] == "brand"]
        self.assertEqual(len(brand_items), 1)
        self.assertEqual(brand_items[0]["title"], "brand_rule:passed")

    def test_brand_not_extracted_when_no_brand_detail(self):
        items = self.extractor.extract({"content_result": {}})
        self.assertEqual([item for item in items if item["type"] == "brand"], [])

    def test_workflow_reports_clean_run_when_no_fallback(self):
        context = {"content_result": {"fallback_used": False}, "research_result": {"fallback_used": False}}
        items = self.extractor.extract(context)
        workflow_item = next(item for item in items if item["type"] == "workflow")
        self.assertEqual(workflow_item["title"], "workflow_run:clean_run")
        self.assertFalse(workflow_item["fallback_used"])

    def test_workflow_reports_fallback_stages(self):
        context = {"content_result": {"fallback_used": True}, "pattern_result": {"fallback_used": True}}
        items = self.extractor.extract(context)
        workflow_item = next(item for item in items if item["type"] == "workflow")
        self.assertEqual(workflow_item["title"], "workflow_run:with_fallback")
        self.assertIn("content", workflow_item["content"]["fallback_stages"])
        self.assertIn("pattern", workflow_item["content"]["fallback_stages"])

    def test_prompt_pattern_extracted_when_prompt_source_present(self):
        context = {"content_result": {"prompt_source": "pattern_aware", "pattern_prompt_meta": {"hook_score": 0.8}}}
        items = self.extractor.extract(context)
        prompt_items = [item for item in items if item["type"] == "prompt_pattern"]
        self.assertEqual(len(prompt_items), 1)

    def test_tool_extracted_when_image_source_present(self):
        context = {"image_strategy_result": {"image_source": "news_thumbnail", "content_type": "news"}}
        items = self.extractor.extract(context)
        tool_items = [item for item in items if item["type"] == "tool"]
        self.assertEqual(len(tool_items), 1)

    def test_image_strategy_extracted_when_content_type_present(self):
        context = {"image_strategy_result": {"content_type": "community", "need_ai_image": False}}
        items = self.extractor.extract(context)
        strategy_items = [item for item in items if item["type"] == "image_strategy"]
        self.assertEqual(len(strategy_items), 1)

    def test_funnel_extracted_when_keyword_present(self):
        context = {
            "research_result": {"keyword": "AI 자동화", "target": "2030", "topic_angle": "실용"},
            "publishing_result": {"platform": "instagram", "status": "publishing_ready"},
        }
        items = self.extractor.extract(context)
        funnel_items = [item for item in items if item["type"] == "funnel"]
        self.assertEqual(len(funnel_items), 1)
        self.assertEqual(funnel_items[0]["content"]["publish_platform"], "instagram")

    def test_funnel_not_extracted_without_keyword(self):
        items = self.extractor.extract({"research_result": {}})
        self.assertEqual([item for item in items if item["type"] == "funnel"], [])


class KnowledgeExtractorRobustnessTests(unittest.TestCase):
    def setUp(self):
        self.extractor = KnowledgeExtractor()

    def test_every_item_has_a_stable_knowledge_id(self):
        context = {"content_result": {"slides": [{"role": "hook", "headline": "제목", "body": ""}]}}
        items_one = self.extractor.extract(context)
        items_two = self.extractor.extract(context)
        self.assertEqual(items_one[0]["knowledge_id"], items_two[0]["knowledge_id"])

    def test_different_content_yields_different_knowledge_id(self):
        context_a = {"content_result": {"slides": [{"role": "hook", "headline": "A", "body": ""}]}}
        context_b = {"content_result": {"slides": [{"role": "hook", "headline": "B", "body": ""}]}}
        item_a = self.extractor.extract(context_a)[0]
        item_b = self.extractor.extract(context_b)[0]
        self.assertNotEqual(item_a["knowledge_id"], item_b["knowledge_id"])

    def test_single_extractor_step_failure_does_not_block_others(self):
        # pattern_result.pattern_plan is a string instead of a dict -- this
        # extractor step must degrade to "no items" without stopping the
        # other 9 extraction steps from running.
        context = {
            "pattern_result": {"pattern_plan": "not-a-dict"},
            "content_result": {"slides": [{"role": "hook", "headline": "제목", "body": ""}]},
        }
        items = self.extractor.extract(context)
        self.assertTrue(any(item["type"] == "hook" for item in items))
        self.assertFalse(any(item["type"] == "pattern" for item in items))

    def test_all_knowledge_types_are_covered_by_a_full_context(self):
        context = {
            "content_result": {
                "slides": [
                    {"role": "hook", "headline": "H", "body": ""},
                    {"role": "cta", "headline": "C", "body": ""},
                ],
                "content_intelligence": {"brand_rule_passed": True, "details": {"brand_rule": {"x": 1}}},
                "prompt_source": "pattern_aware",
                "fallback_used": False,
            },
            "pattern_result": {"pattern_plan": {"pattern_type": "listicle"}, "topic_intelligence": {}},
            "card_news_result": {"layout_result": {"layout_type": "notebook"}},
            "image_strategy_result": {"image_source": "news", "content_type": "news"},
            "research_result": {"keyword": "kw"},
            "publishing_result": {"platform": "instagram", "status": "ready"},
        }
        items = self.extractor.extract(context)
        found_types = {item["type"] for item in items}
        self.assertEqual(found_types, set(KnowledgeExtractor.KNOWLEDGE_TYPES))


class KnowledgeClassifierTests(unittest.TestCase):
    def setUp(self):
        self.classifier = KnowledgeClassifier()

    def test_classify_applies_category_and_cluster_from_topic_intelligence(self):
        items = [{"type": "hook", "title": "x"}]
        context = {"pattern_result": {"topic_intelligence": {"category": "beauty", "cluster": "skincare"}}}
        result = self.classifier.classify(items, context)
        self.assertEqual(result[0]["category"], "beauty")
        self.assertEqual(result[0]["cluster"], "skincare")

    def test_classify_falls_back_to_defaults_when_no_topic_intelligence(self):
        result = self.classifier.classify([{"type": "hook", "title": "x"}], {})
        self.assertEqual(result[0]["category"], KnowledgeClassifier.DEFAULT_CATEGORY)
        self.assertEqual(result[0]["cluster"], KnowledgeClassifier.DEFAULT_CLUSTER)

    def test_classify_tags_include_type_and_keywords(self):
        items = [{"type": "hook", "title": "x"}]
        context = {"pattern_result": {"topic_intelligence": {"keywords": ["AI", "trend"]}}}
        result = self.classifier.classify(items, context)
        self.assertIn("hook", result[0]["tags"])
        self.assertIn("AI", result[0]["tags"])

    def test_classify_tags_are_deduplicated_and_sorted(self):
        items = [{"type": "hook", "title": "x"}]
        context = {"pattern_result": {"topic_intelligence": {"keywords": ["hook", "hook", "AI"]}}}
        result = self.classifier.classify(items, context)
        self.assertEqual(result[0]["tags"], sorted(set(result[0]["tags"])))

    def test_classify_limits_to_first_five_keywords(self):
        items = [{"type": "hook", "title": "x"}]
        keywords = [f"kw{i}" for i in range(10)]
        context = {"pattern_result": {"topic_intelligence": {"keywords": keywords}}}
        result = self.classifier.classify(items, context)
        # tags = {type} + up to 5 keywords, deduplicated/sorted.
        self.assertLessEqual(len(result[0]["tags"]), 6)

    def test_classify_non_list_keywords_does_not_crash(self):
        items = [{"type": "hook", "title": "x"}]
        context = {"pattern_result": {"topic_intelligence": {"keywords": "not-a-list"}}}
        result = self.classifier.classify(items, context)
        self.assertIn("hook", result[0]["tags"])

    def test_classify_preserves_item_count(self):
        items = [{"type": "hook", "title": "a"}, {"type": "cta", "title": "b"}]
        result = self.classifier.classify(items, {})
        self.assertEqual(len(result), 2)

    def test_classify_empty_items_returns_empty_list(self):
        self.assertEqual(self.classifier.classify([], {}), [])

    def test_classify_non_dict_context_does_not_crash(self):
        result = self.classifier.classify([{"type": "hook", "title": "x"}], "not-a-dict")
        self.assertEqual(result[0]["category"], KnowledgeClassifier.DEFAULT_CATEGORY)

    def test_classify_malformed_item_still_yields_safe_defaults(self):
        # A non-dict item must not crash classify(); it degrades to a safe
        # dict carrying only the default category/cluster/tags.
        result = self.classifier.classify(["not-a-dict"], {})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["category"], KnowledgeClassifier.DEFAULT_CATEGORY)
        self.assertEqual(result[0]["tags"], [])

    def test_classify_does_not_mutate_original_items(self):
        original = {"type": "hook", "title": "x"}
        items = [original]
        self.classifier.classify(items, {})
        self.assertNotIn("category", original)


if __name__ == "__main__":
    unittest.main()
