import json
import os
import unittest
from typing import Dict, List

from modules.source_intake.spark_task_queue_builder import run_spark_task_queue


class TestSparkTaskQueueBuilder(unittest.TestCase):
    _WORK_ROOT = os.path.join("tests", "tmp_spark_task_queue")

    def setUp(self):
        os.makedirs(self._WORK_ROOT, exist_ok=True)

    def _write_queue(self, name: str, items: List[Dict[str, object]]) -> str:
        base = os.path.join(self._WORK_ROOT, name)
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, "collector_implementation_queue.json")
        output = os.path.join(base, "spark_task_queue.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"implementation_queue": items}, handle, ensure_ascii=False, indent=2)
        return path, output

    def _tmp_output_path(self, name: str) -> str:
        return os.path.join(self._WORK_ROOT, name, "spark_task_queue.json")

    def test_input_missing(self):
        result = run_spark_task_queue(
            queue_path=os.path.join(self._WORK_ROOT, "missing", "collector_implementation_queue.json"),
            output_path=self._tmp_output_path("missing"),
        )
        self.assertEqual(result["status"], "input_missing")

    def test_selects_only_spark_safe_tasks(self):
        queue_path, output_path = self._write_queue(
            name="safe_tasks",
            items=[
                {"rank": 1, "source_id": "diagnostic_contract_alpha", "status": "NOT_IMPLEMENTED", "recommended_owner": "Spark", "lane_impact": ["a"]},
                {"rank": 2, "source_id": "nate_html_news", "status": "NOT_IMPLEMENTED", "recommended_owner": "Spark", "lane_impact": ["a"]},
                {"rank": 3, "source_id": "browser_workflow", "status": "NOT_IMPLEMENTED", "recommended_owner": "Spark", "lane_impact": ["a"]},
                {"rank": 4, "source_id": "daum_news", "status": "FALLBACK_ONLY", "recommended_owner": "Claude", "lane_impact": ["a"]},
                {"rank": 5, "source_id": "instiz", "status": "FAILED", "recommended_owner": "Spark", "lane_impact": ["a"]},
            ],
        )
        result = run_spark_task_queue(queue_path=queue_path, output_path=output_path)
        queue = result["spark_task_queue"]
        self.assertEqual(result["status"], "completed")
        self.assertEqual([item["source_id"] for item in queue], ["diagnostic_contract_alpha", "instiz"])

    def test_deterministic_sort_and_rank(self):
        queue_path = os.path.join(self._WORK_ROOT, "deterministic", "collector_implementation_queue.json")
        output_path = os.path.join(self._WORK_ROOT, "deterministic", "spark_task_queue.json")
        os.makedirs(os.path.dirname(queue_path), exist_ok=True)
        with open(queue_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "implementation_queue": [
                        {"rank": 11, "source_id": "zeta", "status": "NOT_IMPLEMENTED", "recommended_owner": "Spark", "lane_impact": ["a"]},
                        {"rank": 22, "source_id": "alpha", "status": "FAILED", "recommended_owner": "Spark", "lane_impact": ["a"]},
                        {"rank": 33, "source_id": "alpha", "status": "NOT_IMPLEMENTED", "recommended_owner": "Spark", "lane_impact": ["a"]},
                    ],
                },
                handle,
                ensure_ascii=False,
            )
        first = run_spark_task_queue(queue_path=queue_path, output_path=output_path)
        second = run_spark_task_queue(queue_path=queue_path, output_path=output_path)
        self.assertEqual(first["spark_task_queue"], second["spark_task_queue"])
        self.assertEqual([entry["source_id"] for entry in first["spark_task_queue"]], ["alpha", "alpha", "zeta"])
        self.assertEqual([entry["rank"] for entry in first["spark_task_queue"]], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
