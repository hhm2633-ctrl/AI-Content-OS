"""Focused tests for the selected-candidate production flow."""

import copy
import unittest

from modules.source_intake.selected_candidate_production_flow import (
    run_default_selected_candidate_production_flow,
    run_selected_candidate_production_flow,
)


def _selection(count=1):
    return {
        "accounts": {
            "A": {
                "selected": [
                    {
                        "candidate_id": f"A-{index}",
                        "title": f"뉴스 {index}",
                        "source_urls": ["https://news.example/item"],
                        "likes": 10,
                    }
                    for index in range(count)
                ]
            }
        }
    }


class Provider:
    name = "injected"

    def __init__(self, network=False):
        self.network = network
        self.calls = []

    def discover(self, account, operation, request):
        self.calls.append((account, operation, request["candidate_id"]))
        return {"status": "ok", "network_used": self.network, "assets": []}


class SelectedCandidateProductionFlowTest(unittest.TestCase):
    def test_closes_without_provider_and_does_not_call_bridge(self):
        calls = []
        result = run_selected_candidate_production_flow(
            _selection(), None, lambda value: calls.append(value)
        )
        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["reason_code"], "missing_provider")
        self.assertEqual(calls, [])

    def test_normalizes_without_mutating_owner_selection(self):
        selection = _selection()
        original = copy.deepcopy(selection)
        result = run_selected_candidate_production_flow(selection, Provider(), None)
        normalized = result["normalized_selection"]["accounts"]["A"]["selected"][0]
        self.assertEqual(selection, original)
        self.assertEqual(normalized["source_count"], 1)
        self.assertEqual(normalized["reaction_count"], 10)
        self.assertEqual(result["status"], "discovery_ready")

    def test_account_limit_is_preserved(self):
        provider = Provider()
        result = run_selected_candidate_production_flow(_selection(6), provider, None)
        bucket = result["discovery"]["accounts"]["A"]
        self.assertEqual(bucket["executed"], 4)
        self.assertEqual(bucket["skipped_over_limit"], ["A-4", "A-5"])

    def test_stops_honestly_after_bridge_when_plan_builder_missing(self):
        bridge = lambda discovery: {"status": "ready", "items": ["traceable"]}
        result = run_selected_candidate_production_flow(_selection(), Provider(True), bridge)
        self.assertEqual(result["status"], "media_inputs_ready")
        self.assertEqual(result["reason_code"], "production_plan_builder_required")
        self.assertTrue(result["network_executed"])
        self.assertEqual(result["render_inputs"], [])

    def test_full_injected_chain_returns_render_inputs(self):
        bridge = lambda discovery: {"status": "ready", "items": []}
        plans = lambda selection, discovery, bridged: {
            "plans": [{"candidate_id": "A-0", "schema_version": "test_plan"}]
        }
        render = lambda plan, copy_value: {
            "status": "ready",
            "candidate_id": plan["candidate_id"],
        }
        result = run_selected_candidate_production_flow(
            _selection(), Provider(), bridge, plans, render
        )
        self.assertEqual(result["status"], "render_inputs_ready")
        self.assertEqual(result["render_inputs"][0]["candidate_id"], "A-0")

    def test_bridge_failure_is_additive(self):
        def broken(_discovery):
            raise RuntimeError("bridge failure")

        result = run_selected_candidate_production_flow(_selection(), Provider(), broken)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["reason_code"], "discovery_bridge_failed")
        self.assertEqual(result["failures"][-1]["stage"], "discovery_bridge")

    def test_default_components_are_wired_without_network_or_publish(self):
        class EvidenceProvider:
            name = "evidence_provider"

            def discover(self, account, operation, request):
                return {
                    "status": "ok",
                    "network_used": False,
                    "assets": [
                        {
                            "type": "news_article",
                            "url": "https://news.example/article",
                            "title": request["title"],
                            "description": "기사에 기록된 핵심 설명",
                            "publisher": "news.example",
                        }
                    ],
                }

        result = run_default_selected_candidate_production_flow(
            _selection(), EvidenceProvider()
        )
        self.assertEqual(result["status"], "render_inputs_ready")
        self.assertFalse(result["network_executed"])
        self.assertEqual(len(result["production_plans"]), 1)
        self.assertEqual(
            result["production_plans"][0]["status"], "production_plan_ready"
        )
        self.assertEqual(len(result["render_inputs"]), 1)
        self.assertFalse(result["render_inputs"][0]["publish_executed"])

    def test_default_flow_attaches_story_copy_feed_and_blog_inputs(self):
        selection = {
            "accounts": {
                "C": {
                    "selected": [
                        {
                            "candidate_id": "C-1",
                            "title": "장마철 신발 관리",
                            "category": "생활",
                            "source_urls": ["https://example.test/source"],
                            "commerce_story_status": "ready",
                            "commerce_story_briefs": [
                                {
                                    "product_id": "P-1",
                                    "product_name": "신발 클리너",
                                    "short_story": "비 온 뒤 신발 관리 한 번에",
                                    "practical_topic": "장마철 신발 관리 순서",
                                    "product_role": "신발 관리 콘텐츠 연결",
                                    "season_context": "장마철",
                                    "relation_reason": "습기 관리",
                                    "category": "lifestyle",
                                    "source_shard": "lifestyle",
                                    "row_index": 3,
                                    "blog_seed": {"topic": "장마철 신발 관리", "price": "금지"},
                                }
                            ],
                        }
                    ]
                }
            }
        }

        class EvidenceProvider:
            name = "evidence_provider"

            def discover(self, account, operation, request):
                return {
                    "status": "ok",
                    "network_used": False,
                    "assets": [
                        {
                            "type": "news_article",
                            "url": "https://example.test/source",
                            "title": request["title"],
                            "description": "장마철 관리 자료",
                        }
                    ],
                }

        result = run_default_selected_candidate_production_flow(selection, EvidenceProvider())
        plan = result["production_plans"][0]
        story_input = plan["copy_plan"]["commerce_story_inputs"][0]
        self.assertEqual(story_input["card_copy"]["short_story"], "비 온 뒤 신발 관리 한 번에")
        self.assertIn("신발 클리너", story_input["feed_caption"])
        self.assertNotIn("price", plan["commerce"]["future_blog_seeds"][0])
        self.assertFalse(plan["publish_executed"])


if __name__ == "__main__":
    unittest.main()
