import unittest

from modules.source_intake.owner_ranked_deep_dive_adapter import (
    adapt_owner_ranked_queue_to_selective_contract,
)


class TestOwnerRankedDeepDiveAdapter(unittest.TestCase):
    def test_converts_graded_queue_into_non_executable_contract(self):
        payload = {
            "schema_version": "owner_ranked_deep_dive_queue_v1",
            "requests": [
                {
                    "request_id": "owner_review:candidate-1",
                    "candidate_id": "candidate-1",
                    "grade": "1",
                    "account": "A",
                    "category": "정치",
                    "title": "Title A",
                    "source_urls": ["https://example.com/a"],
                    "requested_media": ["원문 기사", "기사 이미지"],
                    "editorial_target_slide_count": 8,
                    "reference_specimens": [
                        {
                            "reference_id": "ref-owner-1",
                            "approval_status": "owner_approved",
                        }
                    ],
                    "reference_blueprints": {
                        "bp-owner-1": {"blueprint_id": "bp-owner-1"}
                    },
                    "reference_v2_media": {
                        "primary_media": [{"asset_id": "asset-owner-1"}]
                    },
                    "source": "artifacts/latest/collection.json",
                    "status": "waiting_for_deep_discovery",
                },
                {
                    "request_id": "owner_review:blocked",
                    "grade": "exclude",
                    "candidate_id": "blocked",
                    "account": "B",
                },
                {
                    "request_id": "owner_review:unrated",
                    "candidate_id": "unrated",
                },
            ],
        }
        result = adapt_owner_ranked_queue_to_selective_contract(payload)
        self.assertEqual(result["status"], "queue_ready")
        self.assertFalse(result["execution_enabled"])
        self.assertFalse(result["network_executed"])
        self.assertEqual(result["request_count"], 1)

        request = result["requests"][0]
        self.assertEqual(request["candidate_id"], "candidate-1")
        self.assertEqual(request["requested_formats"], ["card_news"])
        self.assertEqual(request["selection_refs"][0]["route_score"], 1.0)
        self.assertEqual(request["required_artifacts"], ["article_body", "source_evidence", "image_rights"])
        self.assertEqual(request["evidence_status"], "owner_reviewed_queue")
        self.assertEqual(request["account"], "A")
        self.assertEqual(request["title"], "Title A")
        self.assertEqual(request["grade"], "1")
        self.assertEqual(request["category"], "정치")
        self.assertEqual(request["source_urls"], ["https://example.com/a"])
        self.assertEqual(request["requested_media"], ["원문 기사", "기사 이미지"])
        self.assertEqual(request["editorial_target_slide_count"], 8)
        self.assertEqual(
            request["reference_specimens"][0]["reference_id"],
            "ref-owner-1",
        )
        self.assertEqual(
            request["reference_blueprints"]["bp-owner-1"]["blueprint_id"],
            "bp-owner-1",
        )
        self.assertEqual(
            request["reference_v2_media"]["primary_media"][0]["asset_id"],
            "asset-owner-1",
        )
        self.assertEqual(
            request["owner_payload"]["reference_specimens"][0]["reference_id"],
            "ref-owner-1",
        )
        source_refs = request["source_refs"]
        kinds = {ref.get("kind") for ref in source_refs}
        values = {ref.get("value") for ref in source_refs}
        self.assertIn("owner_source_url", {ref.get("type") for ref in source_refs})
        self.assertIn("owner_requested_media", {ref.get("type") for ref in source_refs})
        self.assertIn("owner_grade", kinds)
        self.assertIn("Title A", values)

    def test_excluded_and_unrated_entries_are_ignored(self):
        payload = {
            "requests": [
                {"request_id": "owner_review:x", "grade": "exclude", "candidate_id": "x"},
                {"request_id": "owner_review:y", "candidate_id": "y"},
            ]
        }
        result = adapt_owner_ranked_queue_to_selective_contract(payload)
        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["request_count"], 0)

    def test_malformed_input_fails_safely(self):
        result = adapt_owner_ranked_queue_to_selective_contract("not-a-dict")
        self.assertEqual(result["status"], "closed")
        self.assertFalse(result["execution_enabled"])
        self.assertFalse(result["network_executed"])


if __name__ == "__main__":
    unittest.main()
