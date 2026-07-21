import json
import os
import shutil
import uuid
import unittest

from modules.source_intake.source_intake_status_bundle import (
    STATUS_FAILED,
    STATUS_FALLBACK_ONLY,
    STATUS_NOT_IMPLEMENTED,
    STATUS_OK,
    build_source_intake_status_bundle,
    run_source_intake_status_bundle,
)


class TestSourceIntakeStatusBundle(unittest.TestCase):
    def setUp(self):
        self.today = "2099-01-02"
        self.root = os.path.join(".", "source_intake_bundle_tmp", uuid.uuid4().hex)
        os.makedirs(os.path.join(self.root, self.today), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write_json(self, filename, payload):
        path = os.path.join(self.root, self.today, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

    def test_build_status_bundle_with_all_artifacts(self):
        self._write_json("daily_collection_plan.json", {
            "lanes": [
                {"lane_id": "news_society_economy", "shallow_profiles": ["n1"]},
                {"lane_id": "entertainment_news", "shallow_profiles": ["n2"]},
            ],
        })
        self._write_json("daily_shallow_collection.json", {
            "schema_version": "source_intake_shallow_bundle_test",
            "item_count": 7,
            "items": [],
        })
        self._write_json("collection_gap_report.json", {
            "status_counts": {
                STATUS_NOT_IMPLEMENTED: 2,
                STATUS_FALLBACK_ONLY: 1,
                STATUS_FAILED: 1,
                STATUS_OK: 6,
            },
            "status_summary": {
                STATUS_NOT_IMPLEMENTED: [
                    {"source_id": "news_a", "lane_impact": ["news_society_economy"]},
                    {"source_id": "news_b", "lane_impact": ["entertainment_news"]},
                ],
                STATUS_FALLBACK_ONLY: [
                    {"source_id": "news_c", "lane_impact": ["news_society_economy"]},
                ],
                STATUS_FAILED: [
                    {"source_id": "news_d"},
                ],
                STATUS_OK: [
                    {"source_id": "nate_pann"},
                ],
            },
        })
        self._write_json("collector_implementation_queue.json", {
            "implementation_queue": [
                {"source_id": "alpha", "rank": 1, "status": STATUS_NOT_IMPLEMENTED},
                {"source_id": "beta", "rank": 2, "status": STATUS_OK},
                {"source_id": "gamma", "rank": 4, "status": STATUS_FALLBACK_ONLY},
                {"source_id": "delta", "rank": 3, "status": STATUS_FAILED},
                {"source_id": "epsilon", "rank": "5", "status": STATUS_OK},
                {"source_id": "zeta", "rank": "9", "status": STATUS_OK},
            ],
        })
        self._write_json("lane_collection_summary.json", {
            "weak_lanes": ["news_society_economy", "entertainment_news"],
            "lane_summary": {},
        })

        bundle = build_source_intake_status_bundle(today=self.today, root=self.root)

        self.assertEqual(bundle["item_count"], 7)
        self.assertEqual(bundle["status_counts"], {
            STATUS_NOT_IMPLEMENTED: 2,
            STATUS_FALLBACK_ONLY: 1,
            STATUS_FAILED: 1,
            STATUS_OK: 6,
        })
        self.assertEqual(bundle["weak_lanes"], ["news_society_economy", "entertainment_news"])
        self.assertEqual(bundle["top_queue_sources"], ["alpha", "beta", "delta", "gamma", "epsilon"])
        self.assertEqual(bundle["blockers"]["missing_artifacts"], [])
        self.assertEqual(bundle["blockers"]["blocked_lanes"], ["news_society_economy", "entertainment_news"])
        self.assertEqual(bundle["blockers"]["fallback_only_sources"], ["news_c"])
        self.assertEqual(bundle["blockers"]["not_implemented_count"], 2)
        self.assertNotIn("commerce_detail", json.dumps(bundle))

        for present in bundle["artifacts_present"].values():
            self.assertTrue(present)

    def test_build_status_bundle_with_missing_files(self):
        self._write_json("daily_shallow_collection.json", {
            "item_count": 3,
            "source_results": [],
            "items": [],
        })

        bundle = build_source_intake_status_bundle(today=self.today, root=self.root)

        self.assertEqual(bundle["item_count"], 3)
        self.assertEqual(bundle["artifacts_present"], {
            "daily_collection_plan.json": False,
            "daily_shallow_collection.json": True,
            "collection_gap_report.json": False,
            "collector_implementation_queue.json": False,
            "lane_collection_summary.json": False,
        })
        self.assertEqual(bundle["status_counts"], {
            STATUS_NOT_IMPLEMENTED: 0,
            STATUS_FALLBACK_ONLY: 0,
            STATUS_FAILED: 0,
            STATUS_OK: 0,
        })
        self.assertEqual(bundle["weak_lanes"], [])
        self.assertEqual(bundle["top_queue_sources"], [])
        self.assertEqual(bundle["blockers"]["not_implemented_count"], 0)
        self.assertEqual(bundle["blockers"]["fallback_only_sources"], [])
        self.assertCountEqual(
            bundle["blockers"]["missing_artifacts"],
            [
                "daily_collection_plan.json",
                "collection_gap_report.json",
                "collector_implementation_queue.json",
                "lane_collection_summary.json",
            ],
        )

    def test_run_source_intake_status_bundle_writes_file(self):
        self._write_json("daily_shallow_collection.json", {"item_count": 2, "items": []})

        result = run_source_intake_status_bundle(today=self.today, root=self.root)

        self.assertEqual(result["status"], "written")
        self.assertTrue(os.path.isfile(result["bundle_path"]))
        with open(result["bundle_path"], "r", encoding="utf-8") as handle:
            persisted = json.load(handle)
        self.assertEqual(persisted["item_count"], 2)

    def test_smoke_current_source_intake_status_bundle_if_available(self):
        today = "2026-07-14"
        base = os.path.join("storage", "source_intake")
        required = [
            os.path.join(base, today, name)
            for name in [
                "daily_collection_plan.json",
                "daily_shallow_collection.json",
                "collection_gap_report.json",
                "collector_implementation_queue.json",
                "lane_collection_summary.json",
            ]
        ]
        if not all(os.path.exists(path) for path in required):
            self.skipTest("source intake smoke artifacts are not all present")

        bundle = build_source_intake_status_bundle(today=today, root=os.path.join("storage", "source_intake"))

        self.assertEqual(set(bundle.keys()), {
            "artifacts_present",
            "item_count",
            "status_counts",
            "weak_lanes",
            "top_queue_sources",
            "blockers",
        })
        self.assertIn("daily_collection_plan.json", bundle["artifacts_present"])
        self.assertEqual(bundle["blockers"]["missing_artifacts"], [])
        self.assertNotIn("commerce_detail", json.dumps(bundle))

    def test_bundle_has_no_commerce_detail(self):
        self._write_json("daily_shallow_collection.json", {"item_count": 1, "items": []})
        bundle = build_source_intake_status_bundle(today=self.today, root=self.root)

        self.assertNotIn("commerce_detail", json.dumps(bundle))

    def test_bundle_records_fabrication_and_commerce_detail_violations(self):
        self._write_json(
            "daily_shallow_collection.json",
            {"items": [{"source_id": "x", "metrics_origin": "fabricated"}]},
        )
        self._write_json(
            "daily_collection_plan.json",
            {
                "blocked_lanes": ["news_society_economy"],
                "note": "contains commerce_detail marker",
            },
        )
        bundle = build_source_intake_status_bundle(today=self.today, root=self.root)

        violations = bundle["blockers"]["safety_violations"]
        self.assertTrue(any("fabricated" in item for item in violations))
        self.assertTrue(any("commerce_detail" in item for item in violations))


if __name__ == "__main__":
    unittest.main()
