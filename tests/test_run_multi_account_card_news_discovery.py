import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.run_multi_account_card_news_discovery import run_from_paths


class RunMultiAccountCardNewsDiscoveryTest(unittest.TestCase):
    def _payload(self):
        return {
            "schema_version": "daily_shallow_collection_v1",
            "status": "completed",
            "source_results": [
                {"source_id": "news1", "success": True},
                {"source_id": "newsis", "success": False},
            ],
            "items": [
                {"title": "candidate one", "link": "https://example.com/1", "source_id": "news1"},
                {"title": "candidate two", "link": "https://example.com/2", "source_id": "newsis"},
                {"title": "candidate three", "link": "https://example.com/3", "source_id": "news1"},
            ],
        }

    def test_calls_existing_pipeline_and_accounts_for_every_candidate(self):
        pipeline_result = {
            "status": "account_candidates_ready",
            "reason_code": "ok",
            "stages": {
                "collection_eligibility": {
                    "filtered": [
                        {"input_index": 1, "reason_code": "source_not_successful_in_same_payload"}
                    ]
                },
                "clustering": {
                    "status": "ok",
                    "clusters": [
                        {"cluster_id": "cluster-1", "indexes": [0]},
                        {"cluster_id": "cluster-2", "indexes": [1]},
                    ],
                },
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.json"
            output_path = Path(temp_dir) / "output.json"
            payload = self._payload()
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            runner = mock.Mock(return_value=pipeline_result)

            result = run_from_paths(input_path, output_path, pipeline_runner=runner)

            runner.assert_called_once_with(payload)
            self.assertEqual("completed", result["status"])
            preservation = result["candidate_preservation"]
            self.assertEqual(3, preservation["input_count"])
            self.assertEqual(2, preservation["included_count"])
            self.assertEqual(1, preservation["excluded_count"])
            self.assertEqual(0, preservation["held_count"])
            self.assertTrue(preservation["all_candidates_accounted_for"])
            self.assertEqual(3, len(preservation["ledger"]))
            self.assertEqual(result, json.loads(output_path.read_text(encoding="utf-8")))

    def test_holds_eligible_candidates_when_pipeline_does_not_confirm_membership(self):
        pipeline_result = {
            "status": "closed",
            "reason_code": "clustering_closed",
            "stages": {
                "collection_eligibility": {"filtered": []},
                "clustering": {"status": "closed", "clusters": []},
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.json"
            output_path = Path(temp_dir) / "output.json"
            payload = self._payload()
            payload["source_results"][1]["success"] = True
            input_path.write_text(json.dumps(payload), encoding="utf-8")

            result = run_from_paths(input_path, output_path, pipeline_runner=lambda _: pipeline_result)

            self.assertEqual(3, result["candidate_preservation"]["held_count"])
            self.assertEqual(3, result["candidate_preservation"]["accounted_count"])
            self.assertTrue(result["candidate_preservation"]["all_candidates_accounted_for"])

    def test_malformed_input_fails_closed_without_calling_pipeline(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.json"
            output_path = Path(temp_dir) / "output.json"
            input_path.write_text(json.dumps({"items": "not-a-list"}), encoding="utf-8")
            runner = mock.Mock()

            result = run_from_paths(input_path, output_path, pipeline_runner=runner)

            runner.assert_not_called()
            self.assertEqual("closed", result["status"])
            self.assertEqual("unexpected_collection_schema", result["reason_code"])
            self.assertFalse(result["candidate_preservation"]["all_candidates_accounted_for"])
            self.assertTrue(output_path.exists())

    def test_runner_declares_no_side_effectful_stage(self):
        pipeline_result = {
            "status": "closed",
            "reason_code": "no_account_candidates",
            "stages": {
                "collection_eligibility": {"filtered": []},
                "clustering": {
                    "status": "ok",
                    "clusters": [{"cluster_id": "cluster-all", "indexes": [0, 1, 2]}],
                },
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.json"
            output_path = Path(temp_dir) / "output.json"
            payload = self._payload()
            payload["source_results"][1]["success"] = True
            input_path.write_text(json.dumps(payload), encoding="utf-8")

            result = run_from_paths(input_path, output_path, pipeline_runner=lambda _: pipeline_result)

            self.assertFalse(result["external_collection_performed"])
            self.assertFalse(result["deep_fetch_performed"])
            self.assertFalse(result["owner_selection_performed"])
            self.assertFalse(result["render_performed"])
            self.assertFalse(result["publishing_performed"])


if __name__ == "__main__":
    unittest.main()
