import copy
import unittest

from modules.source_intake.discovery_result_render_bridge import (
    run_discovery_result_render_bridge,
)


def _discovery_payload():
    return {
        "status": "completed",
        "accounts": {
            "A": {
                "requested": 1,
                "executed": 1,
                "results": [
                    {
                        "candidate_id": "A-1",
                        "title": "테스트 주제",
                        "operations": [
                            {
                                "operation": "collect_news_images",
                                "artifact_role": "news_image",
                                "assets": [
                                    {
                                        "url": "https://media.example.com/img-ap.jpg",
                                        "source_url": "https://news.example.com/ap-origin",
                                        "source": "Associated Press",
                                        "publisher": "AP",
                                        "media_type": "image",
                                        "published_at": "2026-07-17T09:20:00+09:00",
                                        "rights_status": "unconfirmed",
                                    },
                                    {
                                        "media_url": "https://media.example.com/generated.jpg",
                                        "source_url": "https://official.example.com/article",
                                        "publisher": "Official Brand",
                                        "media_type": "image",
                                        "origin": "generated",
                                        "rights_status": "owned",
                                    },
                                ],
                            },
                            {
                                "operation": "collect_real_comments",
                                "artifact_role": "real_comment",
                                "assets": [
                                    {
                                        "text": "실제 댓글",
                                        "source_url": "https://sns.example.com/post/cmt-1",
                                        "is_real_comment": True,
                                        "published_at": "2026-07-17T09:21:00+09:00",
                                        "channel": "instagram",
                                    },
                                    {
                                        "text": "실제 아닌 댓글",
                                        "source_url": "https://sns.example.com/post/cmt-2",
                                        "is_real_comment": False,
                                        "published_at": "2026-07-17T09:22:00+09:00",
                                    },
                                ],
                            },
                        ],
                    }
                ],
            }
        },
    }


def _broken_payload():
    return {
        "accounts": {
            "A": {
                "results": [
                    {"title": "제목만 있는 후보", "operations": [{"operation": "collect_news_images"}]}
                ]
            }
        }
    }


class DiscoveryResultRenderBridgeTests(unittest.TestCase):
    def test_discovery_result_is_converted_to_traceable_inputs_without_mutation(self):
        payload = _discovery_payload()
        original = copy.deepcopy(payload)
        first = run_discovery_result_render_bridge(payload)
        second = run_discovery_result_render_bridge(payload)

        self.assertEqual(first["status"], "degraded")
        self.assertEqual(first["candidate_count"], 1)
        self.assertEqual(len(first["candidates"]), 1)

        candidate = first["candidates"][0]
        self.assertEqual(candidate["account"], "A")
        self.assertEqual(candidate["candidate_id"], "A-1")
        self.assertEqual(candidate["candidate_title"], "테스트 주제")

        media_inputs = candidate["media_source_inputs"]
        self.assertEqual(len(media_inputs), 4)
        self.assertEqual(media_inputs[0]["source_url"], "https://news.example.com/ap-origin")
        self.assertEqual(media_inputs[0]["media_url"], "https://media.example.com/img-ap.jpg")
        self.assertFalse(media_inputs[0]["render_allowed"])
        self.assertTrue(media_inputs[0]["reference_only"])
        self.assertTrue(media_inputs[0]["ap_reference_only"])
        self.assertEqual(media_inputs[0]["render_restrictions"], ["ap_reference_only", "reference_only"])

        self.assertFalse(media_inputs[1]["render_allowed"])
        self.assertTrue(media_inputs[1]["generated"])
        self.assertIn("generated_synthetic", media_inputs[1]["render_restrictions"])

        self.assertTrue(media_inputs[2]["render_allowed"])
        self.assertEqual(media_inputs[2]["render_restrictions"], [])
        self.assertEqual(media_inputs[2]["real_comment_provenance"]["is_real_comment"], True)
        self.assertEqual(media_inputs[2]["publisher"], None)
        self.assertEqual(media_inputs[2]["channel"], "instagram")

        self.assertFalse(media_inputs[3]["render_allowed"])
        self.assertTrue(media_inputs[3]["real_comment_provenance"]["is_real_comment"] is False)
        self.assertIn("real_comment_provenance_missing", media_inputs[3]["render_restrictions"])

        self.assertEqual(first["totals"]["render_allowed_count"], 1)
        reason_codes = {row["reason_code"] for row in first["diagnostics"]}
        self.assertIn("invalid_real_comment_provenance", reason_codes)
        self.assertEqual(first, second)
        self.assertEqual(payload, original)

    def test_diagnostics_without_invented_values(self):
        payload = _broken_payload()
        result = run_discovery_result_render_bridge(payload)

        self.assertEqual(result["candidate_count"], 1)
        candidate = result["candidates"][0]
        self.assertIsNone(candidate["candidate_id"])
        media_inputs = candidate["media_source_inputs"]
        self.assertEqual(len(media_inputs), 0)
        self.assertTrue(any(item["reason_code"] == "missing_candidate_id" for item in result["diagnostics"]))
        self.assertTrue(any(item["reason_code"] == "operation_assets_missing" for item in candidate["diagnostics"]))
        self.assertNotIn("candidate_operations_missing", {row["reason_code"] for row in candidate["diagnostics"]})

    def test_invalid_top_level_payload_is_closed(self):
        result = run_discovery_result_render_bridge("invalid")
        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["reason_code"], "invalid_discovery_result")
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["candidates"], [])


if __name__ == "__main__":
    unittest.main()
