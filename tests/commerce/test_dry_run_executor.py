import json
import tempfile
import unittest
from pathlib import Path

from modules.commerce.dry_run_executor import DryRunExecutor
from modules.commerce.smartstore_adapter import SmartStoreAdapter
from tests.commerce.fixtures import sample_commerce_result


class DryRunExecutorTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.executor = DryRunExecutor(dryrun_dir=Path(self.tmp_dir.name))
        self.adapter = SmartStoreAdapter()
        self.commerce_result = sample_commerce_result()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_run_never_makes_network_call(self):
        result = self.executor.run(self.adapter, self.commerce_result, persist=False)
        self.assertFalse(result["network_call_made"])

    def test_run_adds_executor_metadata(self):
        result = self.executor.run(self.adapter, self.commerce_result, persist=False)
        self.assertIn("executor_metadata", result)
        self.assertIn("executed_at", result["executor_metadata"])
        self.assertFalse(result["executor_metadata"]["persisted"])
        self.assertIsNone(result["executor_metadata"]["output_path"])

    def test_run_persists_artifact_when_requested(self):
        result = self.executor.run(self.adapter, self.commerce_result, persist=True)
        self.assertTrue(result["executor_metadata"]["persisted"])
        output_path = Path(result["executor_metadata"]["output_path"])
        self.assertTrue(output_path.exists())

    def test_persisted_artifact_is_valid_json_matching_result(self):
        result = self.executor.run(self.adapter, self.commerce_result, persist=True)
        output_path = Path(result["executor_metadata"]["output_path"])
        with open(output_path, "r", encoding="utf-8") as file:
            persisted = json.load(file)
        self.assertEqual(persisted["platform"], "smartstore")
        self.assertEqual(persisted["mode"], "dry_run")

    def test_persisted_artifact_lands_under_request_id_subdirectory(self):
        result = self.executor.run(self.adapter, self.commerce_result, persist=True)
        output_path = Path(result["executor_metadata"]["output_path"])
        self.assertEqual(output_path.parent.name, "smoke_test_001")

    def test_safe_request_id_sanitizes_path_traversal(self):
        self.assertEqual(DryRunExecutor._safe_request_id("../../etc/passwd"), "etc_passwd")

    def test_safe_request_id_falls_back_on_empty_result(self):
        self.assertEqual(DryRunExecutor._safe_request_id(""), "commerce_request")
        self.assertEqual(DryRunExecutor._safe_request_id(None), "commerce_request")

    def test_safe_request_id_truncates_long_values(self):
        long_id = "a" * 200
        self.assertLessEqual(len(DryRunExecutor._safe_request_id(long_id)), 80)

    def test_persist_failure_is_non_fatal(self):
        # Point the dryrun dir at a path that collides with an existing file,
        # so mkdir(parents=True) fails -- run() must still return a result.
        blocker_file = Path(self.tmp_dir.name) / "blocker"
        blocker_file.write_text("x", encoding="utf-8")
        broken_executor = DryRunExecutor(dryrun_dir=blocker_file / "dryrun")

        result = broken_executor.run(self.adapter, self.commerce_result, persist=True)

        self.assertFalse(result["executor_metadata"]["persisted"])
        self.assertIsNone(result["executor_metadata"]["output_path"])
        self.assertIn("payload", result)  # dry_run body still present

    def test_run_never_raises_on_malformed_commerce_result(self):
        result = self.executor.run(self.adapter, {"not": "a valid commerce result"}, persist=False)
        self.assertIn("payload", result)
        self.assertFalse(result["network_call_made"])

    def test_run_never_raises_on_none_commerce_result(self):
        result = self.executor.run(self.adapter, None, persist=False)
        self.assertIn("payload", result)


if __name__ == "__main__":
    unittest.main()
