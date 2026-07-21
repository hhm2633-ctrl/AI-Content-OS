import json
import shutil
from pathlib import Path
import unittest
from unittest import mock

from modules.agent_console import AgentConsole, AgentProfile
from modules.agent_console.spark_host_bridge import (
    SPARK_BRIDGE_SCHEMA,
    SparkHostBridge,
)


def _write_receipt(path: Path, job_id: str, *, envelope_id: str, **overrides):
    payload = {
        "schema_version": "spark_host_receipt_v1",
        "status": "completed",
        "model_reasoning_summary": "none",
        "job_id": job_id,
        "envelope_id": envelope_id,
        "summary": "Spark task completed",
        "outputs": {"token": "REDACTED"},
        "warnings": ["check complete"],
    }
    payload.update(overrides)
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{job_id}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class TestSparkHostBridge(unittest.TestCase):
    def setUp(self):
        self.root = Path.cwd() / ".tmp_test_spark_host_bridge"
        shutil.rmtree(self.root, ignore_errors=True)
        self.root = self.root / "agent_console"
        self.root.mkdir(parents=True)
        self.console = AgentConsole(self.root)
        self.console.register_agent(
            AgentProfile(
                agent_id="spark-1",
                category="all",
                backend="spark",
                model_reasoning_summary="none",
            )
        )
        self.bridge = SparkHostBridge(
            self.console,
            outbox_dir=self.root / "spark_host" / "outbox",
            receipt_dir=self.root / "spark_host" / "receipts",
        )

    def tearDown(self):
        shutil.rmtree(self.root.parent, ignore_errors=True)

    def test_one_job_is_dispatched_as_redacted_safe_envelope(self):
        job_id = self.console.enqueue(
            title="run diagnostic",
            category="news",
            context={"topic": "x", "api_key": "sekret", "password": "1234"},
        )
        envelope = self.bridge.dispatch_one(agent_id="spark-1")
        self.assertIsNotNone(envelope)
        self.assertEqual(envelope["schema_version"], SPARK_BRIDGE_SCHEMA)
        self.assertEqual(envelope["model_reasoning_summary"], "none")
        self.assertNotIn("api_key", envelope["prompt"])
        self.assertNotIn("sekret", envelope["prompt"])
        self.assertNotIn("password", envelope["prompt"])
        self.assertIn("기사 본문", envelope["prompt"])
        self.assertNotIn("감정 변화", envelope["prompt"])
        self.assertEqual(envelope["education_receipt"]["category"], "news")
        self.assertEqual(envelope["education_receipt"]["owner_learning_count"], 5)
        self.assertTrue((self.root / "spark_host" / "outbox" / f"{job_id}.json").exists())
        self.assertEqual(self.console._job(job_id)["status"], "running")
        with self.assertRaises(RuntimeError):
            self.bridge.dispatch_one(agent_id="spark-1")

    def test_summary_mode_none_is_required(self):
        self.console.enqueue(title="invalid", category="news", context={})
        with self.assertRaises(ValueError):
            self.bridge.dispatch_one(agent_id="spark-1", model_reasoning_summary="full")

    def test_registered_non_spark_agent_cannot_use_bridge(self):
        self.console.register_agent(
            AgentProfile(agent_id="local-1", category="all", backend="local")
        )
        self.console.enqueue(title="invalid backend", category="news", context={})
        with self.assertRaises(PermissionError):
            self.bridge.dispatch_one(agent_id="local-1")

    def test_envelope_write_failure_does_not_leave_running_job(self):
        job_id = self.console.enqueue(title="write fails", category="news", context={})
        with mock.patch(
            "modules.agent_console.spark_host_bridge._write_json",
            side_effect=OSError("disk unavailable"),
        ):
            with self.assertRaises(OSError):
                self.bridge.dispatch_one(agent_id="spark-1")
        self.assertEqual(self.console._job(job_id)["status"], "queued")
        self.assertFalse((self.root / "spark_host" / "outbox" / f"{job_id}.json").exists())

    def test_receipt_required_before_completion_and_fails_without_receipt(self):
        job_id = self.console.enqueue(title="needs_receipt", category="news", context={})
        envelope = self.bridge.dispatch_one(agent_id="spark-1")
        self.assertIsNotNone(envelope)

        result = self.bridge.reconcile_receipts(only_job_id=job_id)
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["reconciled_jobs"], [])
        self.assertEqual(self.console._job(job_id)["status"], "running")

        _write_receipt(
            self.root / "spark_host" / "receipts",
            job_id,
            envelope_id=envelope["envelope_id"],
            outputs={"access_token": "tok"},
        )
        result = self.bridge.reconcile_receipts(only_job_id=job_id)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["reconciled_jobs"], [job_id])
        payload = json.loads((self.console.handoff_dir / f"{job_id}.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["summary"], "Spark task completed")
        self.assertEqual(payload["outputs"]["spark_receipt"]["outputs"], {"access_token": "[REDACTED]"})

    def test_mismatched_receipt_cannot_complete_job(self):
        job_id = self.console.enqueue(title="strict_receipt", category="news", context={})
        self.bridge.dispatch_one(agent_id="spark-1")
        _write_receipt(
            self.root / "spark_host" / "receipts",
            job_id,
            envelope_id="wrong-envelope",
        )
        with self.assertRaises(ValueError):
            self.bridge.reconcile_receipts(only_job_id=job_id)
        self.assertEqual(self.console._job(job_id)["status"], "running")


if __name__ == "__main__":
    unittest.main()
