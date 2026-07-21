import tempfile
import unittest
from pathlib import Path

from modules.agent_console.console import AgentConsole
from modules.agent_console.spark_executor import SparkAgentConsoleExecutor


class FakeSparkAdapter:
    def availability(self):
        return {
            "status": "available",
            "model": "gpt-5.3-codex-spark",
            "model_reasoning_summary": "none",
        }

    def execute(self, envelope, *, runtime_dir):
        return {
            "schema_version": "spark_host_receipt_v1",
            "status": "completed",
            "model": "gpt-5.3-codex-spark",
            "model_reasoning_summary": "none",
            "job_id": envelope["job"]["job_id"],
            "envelope_id": envelope["envelope_id"],
            "summary": "automatic Spark cycle completed",
            "outputs": {"verified": True},
            "warnings": [],
        }


class SparkAgentConsoleExecutorTests(unittest.TestCase):
    def test_one_cycle_claims_executes_receipts_and_completes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "console"
            console = AgentConsole(root, repository_root=Path.cwd())
            job_id = console.enqueue(
                title="selected beauty candidate plan",
                category="beauty",
                context={"candidate_id": "C-smoke", "title": "장마철 앞머리"},
            )
            result = SparkAgentConsoleExecutor(console, FakeSparkAdapter()).run_once()
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["job_id"], job_id)
            job = console._job(job_id)
            self.assertEqual(job["status"], "completed")
            self.assertEqual(job["agent_id"], "spark-single")
            self.assertEqual(job["requested_tools"], ["filesystem", "project_cli"])
            self.assertEqual(job["handoff"]["summary"], "automatic Spark cycle completed")
            self.assertTrue(Path(result["receipt_path"]).exists())
            self.assertEqual(console.snapshot()["capability_status"]["backends"]["spark"]["status"], "available")

    def test_second_cycle_is_idle_after_completion(self):
        with tempfile.TemporaryDirectory() as temporary:
            console = AgentConsole(Path(temporary) / "console", repository_root=Path.cwd())
            executor = SparkAgentConsoleExecutor(console, FakeSparkAdapter())
            self.assertEqual(executor.run_once()["status"], "idle")


if __name__ == "__main__":
    unittest.main()
