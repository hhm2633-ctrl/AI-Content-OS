import json
import os
import shutil
import uuid
import unittest

from modules.source_intake.source_intake_artifact_index import (
    ARTIFACTS,
    build_source_intake_artifact_index,
    run_source_intake_artifact_index,
)


class TestSourceIntakeArtifactIndex(unittest.TestCase):
    def setUp(self):
        self.today = "2099-01-02"
        self.root = os.path.join("source_intake_index_tmp", uuid.uuid4().hex)
        self.day_root = os.path.join(self.root, self.today)
        os.makedirs(self.day_root, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write_json(self, filename, payload):
        path = os.path.join(self.day_root, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

    def test_build_artifact_index_all_missing(self):
        artifact_index = build_source_intake_artifact_index(today=self.today, root=self.root)

        self.assertEqual(artifact_index["today"], self.today)
        self.assertEqual(artifact_index["summary"]["artifact_count"], len(ARTIFACTS))
        self.assertEqual(artifact_index["summary"]["present_count"], 0)
        self.assertEqual(artifact_index["summary"]["missing_count"], len(ARTIFACTS))
        self.assertCountEqual(
            artifact_index["summary"]["missing_artifacts"],
            ARTIFACTS,
        )
        for artifact_name in ARTIFACTS:
            entry = artifact_index["artifacts"][artifact_name]
            self.assertFalse(entry["present"])
            self.assertIsNone(entry["size_bytes"])
            self.assertIsNone(entry["last_modified"])
            self.assertIn(artifact_name, entry["path"])

        self.assertNotIn("commerce_detail", json.dumps(artifact_index))

    def test_build_artifact_index_with_some_present(self):
        self._write_json("daily_collection_plan.json", {"schema_version": "v1"})
        self._write_json("source_intake_status_bundle.json", {"ok": True})

        artifact_index = build_source_intake_artifact_index(today=self.today, root=self.root)

        plan_entry = artifact_index["artifacts"]["daily_collection_plan.json"]
        status_entry = artifact_index["artifacts"]["source_intake_status_bundle.json"]
        missing_entry = artifact_index["artifacts"]["daily_shallow_collection.json"]

        self.assertTrue(plan_entry["present"])
        self.assertTrue(status_entry["present"])
        self.assertFalse(missing_entry["present"])
        self.assertGreater(plan_entry["size_bytes"], 0)
        self.assertIsNotNone(plan_entry["last_modified"])
        self.assertEqual(artifact_index["summary"]["present_count"], 2)
        self.assertCountEqual(
            artifact_index["summary"]["present_artifacts"],
            {"daily_collection_plan.json", "source_intake_status_bundle.json"},
        )

        self.assertNotIn("commerce_detail", json.dumps(artifact_index))

    def test_run_artifact_index_writes_json(self):
        self._write_json("collection_gap_report.json", {"status_counts": {}})

        result = run_source_intake_artifact_index(today=self.today, root=self.root)

        self.assertEqual(result["status"], "written")
        self.assertEqual(result["artifact_index_path"], os.path.join(self.day_root, "source_intake_artifact_index.json"))
        self.assertTrue(os.path.isfile(result["artifact_index_path"]))

        with open(result["artifact_index_path"], "r", encoding="utf-8") as handle:
            persisted = json.load(handle)
        self.assertIn("artifacts", persisted)
        self.assertEqual(
            persisted["artifacts"]["collection_gap_report.json"]["present"],
            True,
        )

    def test_source_intake_artifact_index_no_commerce_detail_in_run_output(self):
        result = run_source_intake_artifact_index(today=self.today, root=self.root)

        self.assertNotIn("commerce_detail", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
