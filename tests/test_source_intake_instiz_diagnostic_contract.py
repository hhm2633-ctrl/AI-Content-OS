import json
import os
import shutil
import uuid
import unittest

from modules.source_intake.instiz_diagnostic_contract import (
    DIAGNOSTIC_VERSION,
    DIAGNOSTIC_SOURCE_ID,
    build_instiz_diagnostic_contract,
    run_instiz_diagnostic_contract,
)


class TestInstizDiagnosticContract(unittest.TestCase):
    def setUp(self):
        self.today = "2099-01-02"
        self.root = os.path.join("instiz_diag_tmp", uuid.uuid4().hex)
        os.makedirs(os.path.join(self.root, self.today), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write_json(self, filename, payload):
        path = os.path.join(self.root, self.today, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

    def test_build_instiz_diagnostic_contract_from_rank1_task(self):
        self._write_json(
            "spark_task_queue.json",
            {
                "spark_task_queue": [
                    {
                        "rank": 1,
                        "source_id": DIAGNOSTIC_SOURCE_ID,
                        "status": "FAILED",
                        "lane_impact": ["dopamine_community", "lifestyle_knowledge"],
                        "task_type": "diagnostic_contract",
                        "next_action": "update contract/config and keep gap report stable",
                    }
                ],
            },
        )
        self._write_json(
            "collection_gap_report.json",
            {
                "status_summary": {
                    "FAILED": [
                        {
                            "source_id": DIAGNOSTIC_SOURCE_ID,
                            "skip_reason": "http_403 (2026-07-14 manual check)",
                            "item_count": 0,
                            "attempted": False,
                        }
                    ]
                }
            },
        )
        self._write_json(
            "daily_collection_plan.json",
            {
                "lanes": [
                    {
                        "lane_id": "dopamine_community",
                        "excluded_sources": [
                            {
                                "source_id": DIAGNOSTIC_SOURCE_ID,
                                "attempted": False,
                                "success": False,
                                "skipped": True,
                                "skip_reason": "http_403 (2026-07-14 manual check)",
                                "access_status": "blocked",
                                "workflow_impact": "none",
                            }
                        ],
                    },
                    {
                        "lane_id": "lifestyle_knowledge",
                        "excluded_sources": [
                            {
                                "source_id": DIAGNOSTIC_SOURCE_ID,
                                "attempted": False,
                                "success": False,
                                "skipped": True,
                                "skip_reason": "http_403 (2026-07-14 manual check)",
                                "access_status": "blocked",
                                "workflow_impact": "none",
                            }
                        ],
                    },
                ]
            },
        )

        diagnostic = build_instiz_diagnostic_contract(today=self.today, root=self.root)

        self.assertEqual(diagnostic["schema_version"], DIAGNOSTIC_VERSION)
        self.assertEqual(diagnostic["source_id"], DIAGNOSTIC_SOURCE_ID)
        self.assertEqual(diagnostic["task"]["status"], "FAILED")
        self.assertEqual(diagnostic["task"]["rank"], 1)
        self.assertEqual(diagnostic["current_state"]["collection_status"], "FAILED")
        self.assertEqual(diagnostic["current_state"]["access_state"], "blocked")
        self.assertEqual(
            diagnostic["current_state"]["plan_exclusions"][0]["lane_id"],
            "dopamine_community",
        )
        self.assertIn("lifestyle_knowledge", diagnostic["required_future_collector_inputs"]["required_lane_impact"])
        self.assertIn("access state", diagnostic["required_future_collector_inputs"]["required_preconditions"][0])
        self.assertEqual(diagnostic["required_future_collector_inputs"]["source_profile"]["source_id"], DIAGNOSTIC_SOURCE_ID)

    def test_run_instiz_diagnostic_contract_writes_file(self):
        diagnostic = run_instiz_diagnostic_contract(today=self.today, root=self.root)
        self.assertEqual(diagnostic["status"], "written")
        self.assertTrue(os.path.isfile(diagnostic["output_path"]))

        with open(diagnostic["output_path"], "r", encoding="utf-8") as handle:
            persisted = json.load(handle)
        self.assertEqual(persisted["schema_version"], DIAGNOSTIC_VERSION)

    def test_smoke_current_instiz_diagnostic_if_available(self):
        base = os.path.join("storage", "source_intake", "2026-07-14")
        required = [
            os.path.join(base, "spark_task_queue.json"),
            os.path.join(base, "collection_gap_report.json"),
            os.path.join(base, "daily_collection_plan.json"),
            os.path.join(base, "daily_shallow_collection.json"),
        ]
        if not all(os.path.exists(path) for path in required):
            self.skipTest("storage/source_intake/2026-07-14 diagnostic prerequisites are not available")

        diagnostic = run_instiz_diagnostic_contract(today="2026-07-14", root=os.path.join("storage", "source_intake"))
        self.assertEqual(diagnostic["source_id"], DIAGNOSTIC_SOURCE_ID)
        self.assertEqual(diagnostic["status"], "written")
        self.assertEqual(diagnostic["diagnostic"]["source_id"], DIAGNOSTIC_SOURCE_ID)
        self.assertEqual(diagnostic["diagnostic"]["current_state"]["collection_status"], "FAILED")


if __name__ == "__main__":
    unittest.main()
