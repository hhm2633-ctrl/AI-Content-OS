import json
import os
import shutil
import uuid
import unittest

from modules.source_intake.collection_gap_report import (
    STATUS_FALLBACK_ONLY,
    STATUS_FAILED,
    STATUS_NOT_IMPLEMENTED,
    STATUS_OK,
)
from modules.source_intake.source_intake_consistency_validator import (
    build_source_intake_consistency_report,
    run_source_intake_consistency_report,
)


class TestSourceIntakeConsistencyValidator(unittest.TestCase):
    def setUp(self):
        self.today = "2099-01-02"
        self.root = os.path.join(".", "source_intake_consistency_tmp", uuid.uuid4().hex)
        os.makedirs(os.path.join(self.root, self.today), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write_json(self, filename, payload):
        path = os.path.join(self.root, self.today, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

    def _base_payloads(self):
        return {
            "daily_collection_plan.json": {
                "date": self.today,
                "lanes": [
                    {
                        "lane_id": "news_society_economy",
                        "shallow_profiles": ["src_a", "src_b"],
                        "excluded_sources": [],
                    },
                    {
                        "lane_id": "entertainment_news",
                        "shallow_profiles": ["src_b", "src_c"],
                        "excluded_sources": [{"source_id": "src_z"}],
                    },
                ],
            },
            "daily_shallow_collection.json": {
                "date": self.today,
                "item_count": 4,
                "source_results": [
                    {"source_id": "src_a"},
                    {"source_id": "src_b"},
                    {"source_id": "src_c"},
                    {"source_id": "src_z"},
                ],
                "items": [
                    {"source_id": "src_a"},
                    {"source_id": "src_c"},
                    {"source_id": "src_b"},
                    {"source_id": "src_z"},
                ],
            },
            "collection_gap_report.json": {
                "source_count": 4,
                "status_counts": {
                    STATUS_NOT_IMPLEMENTED: 2,
                    STATUS_FALLBACK_ONLY: 1,
                    STATUS_FAILED: 1,
                    STATUS_OK: 0,
                },
                "status_summary": {
                    STATUS_NOT_IMPLEMENTED: [
                        {"source_id": "src_a", "lane_impact": []},
                        {"source_id": "src_c", "lane_impact": []},
                    ],
                    STATUS_FALLBACK_ONLY: [{"source_id": "src_b", "lane_impact": []}],
                    STATUS_FAILED: [{"source_id": "src_z", "lane_impact": []}],
                    STATUS_OK: [],
                },
                "source_status_by_status": {
                    STATUS_NOT_IMPLEMENTED: [{"source_id": "src_a"}, {"source_id": "src_c"}],
                    STATUS_FALLBACK_ONLY: [{"source_id": "src_b"}],
                    STATUS_FAILED: [{"source_id": "src_z"}],
                    STATUS_OK: [],
                },
            },
            "lane_collection_summary.json": {
                "lane_count": 1,
                "lane_ids": ["news_society_economy"],
                "lane_summary": {
                    "news_society_economy": {
                        "counts_by_status": {
                            STATUS_NOT_IMPLEMENTED: 2,
                            STATUS_FALLBACK_ONLY: 1,
                            STATUS_FAILED: 1,
                            STATUS_OK: 0,
                        },
                        "top_missing_sources": ["src_a", "src_c", "src_z"],
                        "lane_readiness": "BLOCKED",
                    }
                },
                "weak_lanes": ["news_society_economy"],
            },
            "source_intake_status_bundle.json": {
                "status_counts": {
                    STATUS_NOT_IMPLEMENTED: 2,
                    STATUS_FALLBACK_ONLY: 1,
                    STATUS_FAILED: 1,
                    STATUS_OK: 0,
                },
                "item_count": 4,
            },
            "spark_task_queue.json": {
                "schema_version": "spark_task_queue_v1",
                "task_count": 2,
                "spark_task_queue": [
                    {"source_id": "src_a"},
                    {"source_id": "src_b"},
                ],
            },
        }

    def test_build_source_intake_consistency_report_ok(self):
        for name, payload in self._base_payloads().items():
            self._write_json(name, payload)

        report = build_source_intake_consistency_report(today=self.today, root=self.root)
        self.assertEqual(report["status"], "ok", report["mismatches"])
        self.assertEqual(report["counts"]["plan_source_count"], 4)
        self.assertEqual(report["counts"]["shallow_source_count"], 4)
        self.assertEqual(report["counts"]["gap_source_count"], 4)
        self.assertEqual(report["counts"]["status_bundle_status_count_sum"], 4)
        self.assertEqual(report["mismatches"], [])

    def test_excluded_plan_sources_may_be_absent_from_shallow_results(self):
        payloads = self._base_payloads()
        payloads["daily_shallow_collection.json"]["source_results"] = [
            item
            for item in payloads["daily_shallow_collection.json"]["source_results"]
            if item["source_id"] != "src_z"
        ]
        payloads["daily_shallow_collection.json"]["items"] = [
            item
            for item in payloads["daily_shallow_collection.json"]["items"]
            if item["source_id"] != "src_z"
        ]
        for name, payload in payloads.items():
            self._write_json(name, payload)

        report = build_source_intake_consistency_report(today=self.today, root=self.root)
        self.assertEqual(report["status"], "ok", report["mismatches"])
        self.assertEqual(report["source_ids"]["plan_excluded"], ["src_z"])
        self.assertEqual(report["counts"]["plan_active_source_count"], 3)
        self.assertEqual(report["counts"]["shallow_source_count"], 3)

    def test_report_fails_on_date_mismatch(self):
        payloads = self._base_payloads()
        payloads["daily_shallow_collection.json"]["date"] = "2099-01-03"
        for name, payload in payloads.items():
            self._write_json(name, payload)

        report = build_source_intake_consistency_report(today=self.today, root=self.root)
        self.assertEqual(report["status"], "fail_closed")
        self.assertTrue(any(reason.startswith("date_mismatch:daily_collection_plan.json") for reason in report["mismatches"]))

    def test_report_fails_on_source_and_count_mismatch(self):
        payloads = self._base_payloads()
        payloads["collection_gap_report.json"]["status_summary"][STATUS_NOT_IMPLEMENTED].append(
            {"source_id": "src_missing", "lane_impact": []},
        )
        payloads["collection_gap_report.json"]["status_counts"][STATUS_NOT_IMPLEMENTED] = 3
        payloads["collection_gap_report.json"]["source_count"] = 5
        payloads["source_intake_status_bundle.json"]["status_counts"][STATUS_NOT_IMPLEMENTED] = 1
        for name, payload in payloads.items():
            self._write_json(name, payload)

        report = build_source_intake_consistency_report(today=self.today, root=self.root)
        self.assertEqual(report["status"], "fail_closed")
        reasons = "\n".join(report["mismatches"])
        self.assertIn("source_ids_mismatch", reasons)
        self.assertIn("count_mismatch", reasons)

    def test_run_source_intake_consistency_report_writes_file(self):
        payloads = self._base_payloads()
        for name, payload in payloads.items():
            self._write_json(name, payload)

        result = run_source_intake_consistency_report(today=self.today, root=self.root)
        self.assertIn(result["status"], {"ok", "fail_closed"})
        self.assertTrue(os.path.isfile(result["report_path"]))
        with open(result["report_path"], "r", encoding="utf-8") as handle:
            persisted = json.load(handle)
        self.assertIn("mismatches", persisted)
        self.assertIn("counts", persisted)

    def test_smoke_source_intake_consistency_report_if_available(self):
        today = "2026-07-14"
        base = os.path.join("storage", "source_intake")
        required = [
            os.path.join(base, today, artifact)
            for artifact in [
                "daily_collection_plan.json",
                "daily_shallow_collection.json",
                "collection_gap_report.json",
                "lane_collection_summary.json",
                "source_intake_status_bundle.json",
                "spark_task_queue.json",
            ]
        ]
        if not all(os.path.exists(path) for path in required):
            self.skipTest("source intake consistency smoke artifacts are not all present")

        report = build_source_intake_consistency_report(today=today, root=base)
        self.assertIn("status", report)
        self.assertIn("mismatches", report)
        self.assertEqual(len(report["source_ids"]["plan"]), len(set(report["source_ids"]["plan"])))


if __name__ == "__main__":
    unittest.main()
