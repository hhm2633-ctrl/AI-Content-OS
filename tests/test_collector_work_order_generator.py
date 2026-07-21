import os
import shutil
import uuid
import unittest

from modules.source_intake.collector_work_order_generator import generate_collector_work_orders


class TestCollectorWorkOrderGenerator(unittest.TestCase):

    def setUp(self):
        self.base_dir = os.path.join("tests", f"_tmp_collector_work_orders_{uuid.uuid4().hex}")
        os.makedirs(self.base_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.base_dir, ignore_errors=True)

    def write_queue(self, queue, queue_path):
        import json

        os.makedirs(os.path.dirname(queue_path), exist_ok=True)
        with open(queue_path, "w", encoding="utf-8") as handle:
            json.dump({"implementation_queue": queue}, handle, ensure_ascii=False, indent=2)

    def test_missing_input_returns_input_missing(self):
        missing_path = os.path.join(self.base_dir, "missing", "collector_implementation_queue.json")
        result = generate_collector_work_orders(queue_path=missing_path, output_dir=os.path.join(self.base_dir, "out"))
        self.assertEqual(result["status"], "input_missing")
        self.assertEqual(result["queue_path"], missing_path)
        self.assertFalse(os.path.exists(os.path.join(self.base_dir, "out")))

    def test_generates_max_three_markdown_files(self):
        queue_path = os.path.join(self.base_dir, "queue.json")
        output_dir = os.path.join(self.base_dir, "out")
        self.write_queue([
            {"rank": 1, "source_id": "daum_news", "status": "NOT_IMPLEMENTED", "recommended_owner": "Claude"},
            {"rank": 2, "source_id": "nate_news_rank", "status": "NOT_IMPLEMENTED", "recommended_owner": "Claude"},
            {"rank": 3, "source_id": "news1", "status": "FAILED", "recommended_owner": "Claude"},
            {"rank": 4, "source_id": "naver_news", "status": "FALLBACK_ONLY", "recommended_owner": "Spark"},
            {"rank": 5, "source_id": "ruliweb", "status": "NOT_IMPLEMENTED", "recommended_owner": "Codex"},
            {"rank": 6, "source_id": "ppomppu", "status": "NOT_IMPLEMENTED", "recommended_owner": "Claude"},
        ], queue_path)
        result = generate_collector_work_orders(queue_path=queue_path, output_dir=output_dir, max_orders=3)
        files = sorted(f for f in os.listdir(output_dir) if f.endswith(".md"))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(files), 3)
        self.assertEqual(result["generated_count"], 3)
        self.assertEqual(len(result["generated_files"]), 3)
        owned_parts = []
        for item in files:
            with open(os.path.join(output_dir, item), "r", encoding="utf-8") as handle:
                owned_parts.append(handle.read())
        owned = "\n".join(owned_parts)
        self.assertNotIn("naver_news", owned)
        self.assertNotIn("ruliweb", owned)
        for required in ["## objective", "## owned files", "## prohibited files", "## required reading", "## completion checks", "## handoff format"]:
            for item in files:
                with open(os.path.join(output_dir, item), "r", encoding="utf-8") as handle:
                    content = handle.read()
                    self.assertIn(required, content)

    def test_deterministic_filenames_and_stability(self):
        queue_path = os.path.join(self.base_dir, "queue.json")
        output_dir = os.path.join(self.base_dir, "out")
        self.write_queue([
            {"rank": 10, "source_id": "daum_news", "status": "NOT_IMPLEMENTED", "recommended_owner": "Claude"},
            {"rank": 20, "source_id": "daum_news", "status": "FAILED", "recommended_owner": "Claude"},
            {"rank": 30, "source_id": "nate_news_rank", "status": "FAILED", "recommended_owner": "Claude"},
        ], queue_path)
        first = generate_collector_work_orders(queue_path=queue_path, output_dir=output_dir, max_orders=3)
        second = generate_collector_work_orders(queue_path=queue_path, output_dir=output_dir, max_orders=3)
        self.assertEqual([os.path.basename(p) for p in first["generated_files"]], [os.path.basename(p) for p in second["generated_files"]])
        self.assertEqual(len(first["generated_files"]), 3)
        for file_name in first["generated_files"]:
            self.assertIn("_", os.path.basename(file_name))

    def test_no_commerce_detail_section_in_markdown(self):
        queue_path = os.path.join(self.base_dir, "queue.json")
        output_dir = os.path.join(self.base_dir, "out")
        self.write_queue([
            {"rank": 1, "source_id": "dcinside", "status": "NOT_IMPLEMENTED", "recommended_owner": "Claude"},
        ], queue_path)
        result = generate_collector_work_orders(queue_path=queue_path, output_dir=output_dir, max_orders=1)
        file_path = result["generated_files"][0]
        with open(file_path, "r", encoding="utf-8") as handle:
            content = handle.read().lower()
        self.assertNotIn("commerce_detail", content)


if __name__ == "__main__":
    unittest.main()
