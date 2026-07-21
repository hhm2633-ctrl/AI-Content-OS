import json
import os
import unittest

from modules.source_intake.lane_collection_summary_runner import run_lane_collection_summary


class TestLaneCollectionSummaryRunner(unittest.TestCase):
    _WORK_ROOT = os.path.join("storage", "lane_collection_summary_runner_test")
    _TODAY = "2026-07-14"

    def setUp(self):
        os.makedirs(self._WORK_ROOT, exist_ok=True)

    def _work_dir(self, test_name: str) -> str:
        return os.path.join(self._WORK_ROOT, test_name, self._TODAY)

    def _write_gap_report(self, test_name: str) -> str:
        work_dir = self._work_dir(test_name)
        os.makedirs(work_dir, exist_ok=True)
        gap_report_path = os.path.join(work_dir, "collection_gap_report.json")
        payload = {
            "status_summary": {
                "NOT_IMPLEMENTED": [
                    {"source_id": "news_feed", "lane_impact": ["news"], "status": "NOT_IMPLEMENTED"},
                    {"source_id": "style_feed", "lane_impact": ["style"], "status": "NOT_IMPLEMENTED"},
                ],
                "FALLBACK_ONLY": [],
                "FAILED": [
                    {"source_id": "finance_feed", "lane_impact": ["finance"], "status": "FAILED"},
                ],
                "OK": [],
            },
            "recommended_implementation_order": [
                {"source_id": "news_feed", "status": "NOT_IMPLEMENTED", "lane_impact": ["news"]},
                {"source_id": "style_feed", "status": "NOT_IMPLEMENTED", "lane_impact": ["style"]},
                {"source_id": "finance_feed", "status": "FAILED", "lane_impact": ["finance"]},
            ],
            "all_lanes": ["news", "style", "finance", "commerce"],
        }
        with open(gap_report_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
        return work_dir

    def test_missing_input_returns_input_missing_and_writes_nothing(self):
        root = os.path.join(self._WORK_ROOT, "missing_input")
        result = run_lane_collection_summary(
            gap_report_path=os.path.join(root, self._TODAY, "missing.json"),
            today=self._TODAY,
            output_root=root,
        )

        self.assertEqual(result["status"], "input_missing")
        self.assertFalse(os.path.exists(os.path.join(root, self._TODAY, "lane_collection_summary.json")))

    def test_successful_write(self):
        work_dir = self._write_gap_report("successful_write")
        result = run_lane_collection_summary(
            gap_report_path=os.path.join(work_dir, "collection_gap_report.json"),
            today=self._TODAY,
            output_root=self._WORK_ROOT,
        )
        output_path = os.path.join(self._WORK_ROOT, self._TODAY, "lane_collection_summary.json")

        self.assertEqual(result["status"], "written")
        self.assertTrue(os.path.exists(output_path))
        self.assertEqual(result["lane_collection_summary_path"], output_path)

    def test_written_json_is_valid(self):
        work_dir = self._write_gap_report("written_json_is_valid")
        result = run_lane_collection_summary(
            gap_report_path=os.path.join(work_dir, "collection_gap_report.json"),
            today=self._TODAY,
            output_root=self._WORK_ROOT,
        )
        self.assertEqual(result["status"], "written")

        with open(result["lane_collection_summary_path"], "r", encoding="utf-8") as handle:
            loaded = json.load(handle)

        self.assertEqual(loaded["schema_version"], "lane_collection_summary_v1")
        self.assertIn("lane_summary", loaded)
        self.assertIn("weak_lanes", loaded)
        self.assertIsInstance(loaded["weak_lanes"], list)

    def test_weak_lanes_present(self):
        work_dir = self._write_gap_report("weak_lanes_present")
        result = run_lane_collection_summary(
            gap_report_path=os.path.join(work_dir, "collection_gap_report.json"),
            today=self._TODAY,
            output_root=self._WORK_ROOT,
        )

        self.assertEqual(result["status"], "written")
        payload = result["lane_collection_summary"]
        self.assertTrue(payload["weak_lanes"])
        self.assertIn("commerce", payload["weak_lanes"])

    def test_no_commerce_detail(self):
        work_dir = self._write_gap_report("no_commerce_detail")
        result = run_lane_collection_summary(
            gap_report_path=os.path.join(work_dir, "collection_gap_report.json"),
            today=self._TODAY,
            output_root=self._WORK_ROOT,
        )

        self.assertEqual(result["status"], "written")
        for lane_summary in result["lane_collection_summary"]["lane_summary"].values():
            self.assertNotIn("commerce_detail", lane_summary)


if __name__ == "__main__":
    unittest.main()
