import copy
import unittest

from modules.source_intake.selective_deep_dive_queue import (
    build_selective_deep_dive_queue,
)


class TestSelectiveDeepDiveQueue(unittest.TestCase):
    def test_malformed_input_fails_closed(self):
        result = build_selective_deep_dive_queue(None)
        self.assertEqual(result["status"], "closed")
        self.assertFalse(result["execution_enabled"])
        self.assertFalse(result["network_executed"])

    def test_selected_formats_are_grouped_without_execution(self):
        portfolio = {
            "selected_by_format": {
                "card_news": [
                    {
                        "candidate_id": "c1",
                        "cluster_id": "cluster-1",
                        "category_id": "entertainment_news",
                        "route_score": 0.8,
                        "route_confidence": 0.7,
                        "risk_status": "reviewed",
                        "evidence_status": "NEEDS_EVIDENCE",
                        "source_refs": [{"source_id": "news1"}],
                    }
                ],
                "shorts_reels": [
                    {
                        "candidate_id": "c1",
                        "cluster_id": "cluster-1",
                        "route_score": 0.75,
                        "route_confidence": 0.6,
                        "risk_status": "reviewed",
                    }
                ],
                "commerce": [],
            }
        }
        result = build_selective_deep_dive_queue(portfolio)
        self.assertEqual(result["status"], "queue_ready")
        self.assertEqual(result["request_count"], 1)
        request = result["requests"][0]
        self.assertEqual(request["requested_formats"], ["card_news", "shorts_reels"])
        self.assertIn("article_body", request["required_artifacts"])
        self.assertIn("image_rights", request["required_artifacts"])
        self.assertIn("visual_asset_rights", request["required_artifacts"])
        self.assertFalse(request["execution_enabled"])
        self.assertFalse(request["network_executed"])

    def test_risk_blocked_candidate_never_enters_queue(self):
        result = build_selective_deep_dive_queue(
            {
                "selected_by_format": {
                    "card_news": [
                        {"candidate_id": "blocked", "risk_status": "BLOCKED"}
                    ]
                }
            }
        )
        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["request_count"], 0)
        self.assertEqual(result["blocked"][0]["reason_code"], "risk_blocked")

    def test_unknown_risk_never_enters_queue(self):
        result = build_selective_deep_dive_queue(
            {"selected_by_format": {"card_news": [{"candidate_id": "unknown"}]}}
        )
        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["blocked"][0]["reason_code"], "risk_not_cleared")

    def test_input_is_not_mutated(self):
        portfolio = {
            "selected_by_format": {
                "commerce": [
                    {
                        "candidate_id": "c2",
                        "risk_status": "reviewed",
                        "source_refs": [{"source_id": "ppomppu"}],
                    }
                ]
            }
        }
        expected = copy.deepcopy(portfolio)
        build_selective_deep_dive_queue(portfolio)
        self.assertEqual(portfolio, expected)


if __name__ == "__main__":
    unittest.main()
