import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_owner_candidate_report import build_report


class BuildOwnerCandidateReportTest(unittest.TestCase):
    def test_reports_every_raw_candidate_with_stage1_state_and_account(self):
        raw = {
            "schema_version": "daily_shallow_collection_v1",
            "status": "completed",
            "items": [
                {"title": "news one", "link": "https://example.com/1", "source_id": "news1", "category": "news"},
                {"title": "fashion two", "link": "https://example.com/2", "source_id": "fashionn", "category": "fashion"},
                {"title": "held three", "link": "https://example.com/3", "source_id": "newsis", "category": "society"},
            ],
        }
        stage1 = {
            "candidate_preservation": {
                "input_count": 3,
                "ledger": [
                    {"input_index": 0, "title": "news one", "url": "https://example.com/1", "disposition": "included", "reason_code": "accepted_into_discovery_cluster"},
                    {"input_index": 1, "title": "fashion two", "url": "https://example.com/2", "disposition": "excluded", "reason_code": "source_not_successful_in_same_payload"},
                    {"input_index": 2, "title": "held three", "url": "https://example.com/3", "disposition": "held", "reason_code": "pipeline_did_not_confirm_cluster_membership"},
                ],
            },
            "pipeline_result": {
                "stages": {
                    "account_routing": {
                        "items": [
                            {"title": "news one", "link": "https://example.com/1", "account_id": "account_a_news"},
                        ]
                    }
                }
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw_path = root / "raw.json"
            pipeline_path = root / "stage1.json"
            output_path = root / "owner.md"
            raw_path.write_text(json.dumps(raw), encoding="utf-8")
            pipeline_path.write_text(json.dumps(stage1), encoding="utf-8")

            result = build_report(raw_path, pipeline_path, output_path)
            report = output_path.read_text(encoding="utf-8")

            self.assertEqual(3, result["raw_item_count"])
            self.assertEqual(3, result["reported_item_count"])
            self.assertEqual({"excluded": 1, "held": 1, "included": 1}, result["candidate_state_counts"])
            self.assertEqual(3, result["stage1_accounting_rows_seen"])
            self.assertEqual(3, report.count("State: `"))
            self.assertIn("Account: `account_a_news`", report)
            self.assertIn("Reason: `source_not_successful_in_same_payload`", report)
            self.assertIn("Reason: `pipeline_did_not_confirm_cluster_membership`", report)


if __name__ == "__main__":
    unittest.main()
