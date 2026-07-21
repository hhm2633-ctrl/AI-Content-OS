import json
import os
import unittest

from modules.source_intake.collection_gap_runner import run_collection_gap_report


class TestCollectionGapRunner(unittest.TestCase):
    _WORK_ROOT = os.path.join("storage", "collection_gap_runner_test")

    def setUp(self):
        os.makedirs(self._WORK_ROOT, exist_ok=True)

    def _input_path(self, test_name: str) -> str:
        target = os.path.join(self._WORK_ROOT, test_name, "2026-07-14")
        os.makedirs(target, exist_ok=True)
        return os.path.join(target, "daily_shallow_collection.json")

    def test_missing_input_returns_input_missing_and_no_outputs(self):
        missing_path = os.path.join(self._WORK_ROOT, "missing", "2026-07-14", "missing.json")
        result = run_collection_gap_report(
            collection_result_path=missing_path,
            today="2026-07-14",
            output_root=os.path.join(self._WORK_ROOT, "missing"),
        )

        self.assertEqual(result["status"], "input_missing")
        self.assertFalse(os.path.exists(os.path.join(self._WORK_ROOT, "missing", "2026-07-14", "collection_gap_report.json")))
        self.assertFalse(os.path.exists(os.path.join(self._WORK_ROOT, "missing", "2026-07-14", "collector_implementation_queue.json")))

    def test_successful_run_writes_report_and_queue(self):
        work_root = os.path.join(self._WORK_ROOT, "successful_run")
        payload = {
            "plan": {
                "lanes": [
                    {"lane_id": "news", "shallow_profiles": ["alpha", "beta", "gamma"]},
                ]
            },
            "source_results": [
                {"source_id": "alpha", "attempted": True, "success": True, "count": 2},
                {"source_id": "beta", "attempted": False, "success": False, "skip_reason": "collector_not_implemented", "count": 0},
                {"source_id": "gamma", "attempted": True, "success": False, "skip_reason": "timeout", "count": 0},
            ],
            "items": [
                {"source_id": "alpha", "is_fallback": True, "collection_method": "settings_keyword_fallback"},
            ],
        }
        input_path = self._input_path("successful_run")
        with open(input_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

        result = run_collection_gap_report(
            collection_result_path=input_path,
            today="2026-07-14",
            output_root=work_root,
        )

        self.assertEqual(result["status"], "completed")
        report_path = result["collection_gap_report_path"]
        queue_path = result["collector_implementation_queue_path"]
        self.assertTrue(os.path.exists(report_path))
        self.assertTrue(os.path.exists(queue_path))

        with open(report_path, "r", encoding="utf-8") as handle:
            report_payload = json.load(handle)
        with open(queue_path, "r", encoding="utf-8") as handle:
            queue_payload = json.load(handle)

        self.assertIn("recommended_implementation_order", report_payload)
        self.assertIn("implementation_queue", queue_payload)
        self.assertTrue(queue_payload["implementation_queue"])

    def test_queue_excludes_ok(self):
        work_root = os.path.join(self._WORK_ROOT, "queue_excludes_ok")
        payload = {
            "plan": {"lanes": [{"lane_id": "news", "shallow_profiles": ["ok_source", "todo_source"]}]},
            "source_results": [
                {"source_id": "ok_source", "attempted": True, "success": True, "count": 1},
                {"source_id": "todo_source", "attempted": False, "success": False, "skip_reason": "collector_not_implemented", "count": 0},
            ],
            "items": [
                {"source_id": "ok_source", "visible_metrics": {"views": 1}},
            ],
        }
        input_path = self._input_path("queue_excludes_ok")
        with open(input_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

        result = run_collection_gap_report(
            collection_result_path=input_path,
            today="2026-07-14",
            output_root=work_root,
        )

        queue = result["implementation_queue"]
        self.assertTrue(all(entry["status"] != "OK" for entry in queue))
        self.assertFalse(any(entry["source_id"] == "ok_source" for entry in queue))

    def test_queue_rank_deterministic(self):
        work_root = os.path.join(self._WORK_ROOT, "queue_rank_deterministic")
        payload = {
            "plan": {
                "lanes": [
                    {"lane_id": "a", "shallow_profiles": ["zeta", "beta"]},
                    {"lane_id": "b", "shallow_profiles": ["alpha"]},
                ]
            },
            "source_results": [
                {"source_id": "zeta", "attempted": False, "success": False, "skip_reason": "collector_not_implemented", "count": 0},
                {"source_id": "beta", "attempted": False, "success": False, "skip_reason": "collector_not_implemented", "count": 0},
                {"source_id": "alpha", "attempted": False, "success": False, "skip_reason": "collector_not_implemented", "count": 0},
            ],
            "items": [],
        }
        input_path = self._input_path("queue_rank_deterministic")
        with open(input_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

        first = run_collection_gap_report(collection_result_path=input_path, today="2026-07-14", output_root=work_root)
        second = run_collection_gap_report(collection_result_path=input_path, today="2026-07-14", output_root=work_root)
        self.assertEqual(first["implementation_queue"], second["implementation_queue"])
        self.assertEqual(
            [entry["rank"] for entry in first["implementation_queue"]],
            list(range(1, len(first["implementation_queue"]) + 1)),
        )
        self.assertEqual(
            [entry["source_id"] for entry in first["implementation_queue"]],
            sorted([entry["source_id"] for entry in first["implementation_queue"]]),
        )

    def test_queue_has_no_commerce_detail(self):
        work_root = os.path.join(self._WORK_ROOT, "no_commerce_detail")
        payload = {
            "plan": {"lanes": [{"lane_id": "news", "shallow_profiles": ["beta"]}]},
            "source_results": [
                {"source_id": "beta", "attempted": False, "success": False, "skip_reason": "collector_not_implemented", "count": 0},
            ],
            "items": [],
        }
        input_path = self._input_path("no_commerce_detail")
        with open(input_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

        result = run_collection_gap_report(
            collection_result_path=input_path,
            today="2026-07-14",
            output_root=work_root,
        )

        for entry in result["implementation_queue"]:
            self.assertNotIn("commerce_detail", entry)


if __name__ == "__main__":
    unittest.main()
