import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.agent_console import (
    AgentConsole,
    AgentLimits,
    AgentProfile,
    Handoff,
    LazyToolRegistry,
    ToolSpec,
)
from modules.agent_console.tool_manifest import BoundedFilesystemAdapter
from modules.agent_console.executor import AgentConsoleExecutor, CLAUDE_AGENT_ID, ClaudeCliAdapter


class TestAgentConsole(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "agent_console"

    def tearDown(self):
        self.temp.cleanup()

    def _profile(self, agent_id="news-1", category="news", **kwargs):
        return AgentProfile(agent_id=agent_id, category=category, backend="local", **kwargs)

    def test_parallel_and_sequential_category_chains(self):
        console = AgentConsole(self.root)
        for category in ("news", "story", "fashion", "beauty"):
            console.register_agent(self._profile(f"{category}-1", category))
        parallel = console.enqueue_category_chain(
            {category: {"candidate_count": 2} for category in ("news", "story", "fashion", "beauty")}
        )
        self.assertEqual(len(parallel), 4)
        self.assertEqual(len(console.ready_jobs()), 4)

        other = AgentConsole(Path(self.temp.name) / "sequential")
        sequential = other.enqueue_category_chain(
            {category: {} for category in ("news", "story", "fashion", "beauty")},
            sequential=True,
        )
        self.assertEqual(len(sequential), 4)
        self.assertEqual([job["category"] for job in other.ready_jobs()], ["news"])

    def test_context_is_isolated_and_secrets_are_redacted(self):
        console = AgentConsole(self.root)
        console.register_agent(self._profile())
        first = console.enqueue(title="first", category="news", context={"topic": "A", "api_key": "secret"})
        second = console.enqueue(title="second", category="news", context={"topic": "B"})
        claimed = console.claim_next("news-1")
        self.assertEqual(claimed["job"]["job_id"], first)
        self.assertEqual(claimed["context"], {"topic": "A", "api_key": "[REDACTED]"})
        self.assertNotEqual(console._job(first)["context_path"], console._job(second)["context_path"])

    def test_short_json_handoff_unlocks_dependency(self):
        console = AgentConsole(self.root)
        console.register_agent(self._profile())
        first = console.enqueue(title="first", category="news", context={})
        second = console.enqueue(title="second", category="news", context={}, depends_on=[first])
        console.claim_next("news-1")
        console.complete(first, Handoff("candidate list ready", {"count": 4, "access_token": "x"}))
        self.assertEqual([job["job_id"] for job in console.ready_jobs()], [second])
        payload = json.loads((self.root / "handoffs" / f"{first}.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["outputs"]["access_token"], "[REDACTED]")

    def test_deferred_tool_factory_is_not_eager(self):
        calls = []
        tools = LazyToolRegistry()
        tools.register(ToolSpec("graphify", "local", "query"), lambda: calls.append("loaded") or object())
        console = AgentConsole(self.root, tools=tools)
        console.register_agent(self._profile(allowed_tools=("graphify",)))
        job_id = console.enqueue(
            title="module architecture query", category="news", context={}, requested_tools=("graphify",)
        )
        console.claim_next("news-1")
        self.assertEqual(calls, [])
        first = console.load_tool(job_id, "graphify")
        second = console.load_tool(job_id, "graphify")
        self.assertIs(first, second)
        self.assertEqual(calls, ["loaded"])

    def test_safe_tools_are_assigned_automatically_at_claim_time(self):
        console = AgentConsole(self.root, repository_root=Path.cwd())
        console.register_agent(self._profile(category="all", allowed_tools=("filesystem", "project_cli", "graphify", "hyperframes")))
        job_id = console.enqueue(title="candidate research", category="beauty", context={"candidate_id": "C-1"})
        claimed = console.claim_next("news-1")
        self.assertEqual(claimed["job"]["job_id"], job_id)
        self.assertEqual(claimed["job"]["requested_tools"], ["filesystem", "project_cli"])
        self.assertEqual(claimed["job"]["tool_assignment"]["status"], "assigned")
        self.assertEqual(console.tools.loaded_tool_ids, ())

    def test_unrequested_or_disallowed_tool_is_blocked(self):
        tools = LazyToolRegistry()
        tools.register(ToolSpec("browser", "host", "research"), lambda: object())
        console = AgentConsole(self.root, tools=tools)
        console.register_agent(self._profile(allowed_tools=()))
        job_id = console.enqueue(title="research", category="news", context={}, requested_tools=("browser",))
        self.assertIsNone(console.claim_next("news-1"))
        self.assertEqual(console._job(job_id)["status"], "blocked")

    def test_step_limit_and_retry_limit(self):
        console = AgentConsole(self.root)
        console.register_agent(
            self._profile(limits=AgentLimits(max_steps=1, timeout_seconds=60, max_retries=1))
        )
        job_id = console.enqueue(title="bounded", category="news", context={})
        console.claim_next("news-1")
        console.record_step(job_id, label="one")
        with self.assertRaises(RuntimeError):
            console.record_step(job_id, label="two")
        self.assertEqual(console._job(job_id)["status"], "failed")

        retry_job = console.enqueue(title="retry", category="news", context={})
        console.claim_next("news-1")
        console.fail(retry_job, "temporary", retryable=True)
        self.assertEqual(console._job(retry_job)["status"], "queued")
        console.claim_next("news-1")
        console.fail(retry_job, "temporary again", retryable=True)
        self.assertEqual(console._job(retry_job)["status"], "failed")

    def test_timeout_sweep_requeues_once(self):
        console = AgentConsole(self.root)
        console.register_agent(
            self._profile(limits=AgentLimits(max_steps=2, timeout_seconds=1, max_retries=1))
        )
        job_id = console.enqueue(title="timeout", category="news", context={})
        console.claim_next("news-1")
        future = datetime.now(timezone.utc) + timedelta(seconds=3)
        self.assertEqual(console.sweep_timeouts(now=future), [job_id])
        self.assertEqual(console._job(job_id)["status"], "queued")

    def test_claude_and_spark_session_guards(self):
        console = AgentConsole(self.root)
        console.register_agent(
            AgentProfile("claude-fashion", "fashion", "claude_cli", session_key="single-reusable")
        )
        with self.assertRaises(ValueError):
            console.register_agent(
                AgentProfile("claude-beauty", "beauty", "claude_cli", session_key="second")
            )
        with self.assertRaises(ValueError):
            AgentProfile("spark-story", "story", "spark")
        spark = AgentProfile(
            "spark-story", "story", "spark", model_reasoning_summary="none"
        )
        self.assertEqual(spark.model_reasoning_summary, "none")

    def test_dashboard_contains_queue_status_and_result(self):
        console = AgentConsole(self.root)
        console.register_agent(self._profile())
        job_id = console.enqueue(title="current news", category="news", context={})
        console.claim_next("news-1")
        console.complete(job_id, Handoff("four candidates returned"))
        html = console.dashboard_path.read_text(encoding="utf-8")
        self.assertIn("Agent Console v1", html)
        self.assertIn("current news", html)
        self.assertIn("four candidates returned", html)
        self.assertIn("completed", html)

    def test_owner_review_queue_sync_creates_updates_and_cancels_without_execution(self):
        console = AgentConsole(self.root)
        queue = {
            "schema_version": "owner_ranked_deep_dive_queue_v1",
            "updated_at": "2026-07-18T00:00:00Z",
            "requests": [
                {"request_id": "owner_review:A-1", "candidate_id": "A-1", "account": "A", "category": "국내뉴스", "title": "뉴스", "grade": "1"},
                {"request_id": "owner_review:C-1", "candidate_id": "C-1", "account": "C", "category": "향수", "title": "향수", "grade": "2"},
            ],
        }
        self.assertEqual(console.sync_owner_review_queue(queue), {"created": 2, "updated": 0, "cancelled": 0})
        jobs = {job["candidate_id"]: job for job in console.snapshot()["jobs"]}
        self.assertEqual(jobs["A-1"]["category"], "news")
        self.assertEqual(jobs["C-1"]["category"], "beauty")
        self.assertEqual(jobs["A-1"]["status"], "awaiting_second_stage")
        self.assertEqual(jobs["A-1"]["execution_adapter"], "not_connected")
        self.assertEqual(console.ready_jobs(), [])

        promoted = console.promote_owner_review_jobs(["owner_review:A-1"])
        self.assertEqual(promoted, [jobs["A-1"]["job_id"]])
        self.assertEqual([job["job_id"] for job in console.ready_jobs()], promoted)

        queue["requests"] = [queue["requests"][1]]
        self.assertEqual(console.sync_owner_review_queue(queue), {"created": 0, "updated": 1, "cancelled": 1})
        jobs = {job["candidate_id"]: job for job in console.snapshot()["jobs"]}
        self.assertEqual(jobs["A-1"]["status"], "cancelled")

    def test_legacy_owner_review_queue_is_held_until_explicit_promotion(self):
        console = AgentConsole(self.root)
        job_id = console.enqueue(title="legacy", category="news", context={"execution_enabled": False})
        job = console._job(job_id)
        job.update(
            {
                "source": "owner_review",
                "source_request_id": "owner_review:A-legacy",
                "candidate_id": "A-legacy",
            }
        )
        console._save()

        self.assertEqual(console.hold_unselected_owner_review_jobs(), [job_id])
        self.assertEqual(console.ready_jobs(), [])
        self.assertEqual(console.hold_unselected_owner_review_jobs(), [])

    def test_reconcile_owner_review_selection_promotes_selected_and_holds_rest(self):
        console = AgentConsole(self.root)
        queue = {
            "schema_version": "owner_ranked_deep_dive_queue_v1",
            "requests": [
                {"request_id": "owner_review:A-1", "candidate_id": "A-1", "account": "A", "category": "news", "title": "one", "grade": "1"},
                {"request_id": "owner_review:A-2", "candidate_id": "A-2", "account": "A", "category": "news", "title": "two", "grade": "1"},
            ],
        }
        console.sync_owner_review_queue(queue)
        result = console.reconcile_owner_review_selection(["owner_review:A-2"])
        self.assertEqual(len(result["promoted"]), 1)
        jobs = {job["candidate_id"]: job for job in console.snapshot()["jobs"]}
        self.assertEqual(jobs["A-2"]["status"], "queued")
        self.assertTrue(jobs["A-2"]["execution_approved"])
        self.assertEqual(jobs["A-1"]["status"], "awaiting_second_stage")
        self.assertFalse(jobs["A-1"]["execution_approved"])
        self.assertEqual(console.reconcile_owner_review_selection(["owner_review:A-2"])["promoted"], [])

    def test_default_manifest_connects_only_real_bounded_adapters(self):
        console = AgentConsole(self.root, repository_root=Path.cwd())
        manifest = console.snapshot()["tool_manifest"]
        self.assertTrue(manifest["filesystem"]["loader_registered"])
        self.assertTrue(manifest["project_cli"]["loader_registered"])
        self.assertFalse(manifest["browser"]["loader_registered"])
        self.assertNotIn("naeo_blog", manifest)

    def test_bounded_filesystem_rejects_parent_and_absolute_paths(self):
        root = Path(self.temp.name) / "repo"
        root.mkdir()
        (root / "safe.txt").write_text("safe", encoding="utf-8")
        adapter = BoundedFilesystemAdapter(root)
        self.assertEqual(adapter.read_text("safe.txt"), "safe")
        with self.assertRaises(PermissionError):
            adapter.read_text("../outside.txt")
        with self.assertRaises(PermissionError):
            adapter.read_text(root / "safe.txt")

    def test_external_tool_manifests_pin_sources_and_keep_render_blocked(self):
        repository = Path.cwd()
        hyperframes = json.loads(
            (repository / "config" / "external_tools" / "hyperframes_local.json").read_text(encoding="utf-8")
        )
        agency = json.loads(
            (repository / "config" / "external_tools" / "agency_agents_local.json").read_text(encoding="utf-8")
        )
        self.assertEqual(hyperframes["upstream"]["official_skill_count"], 19)
        self.assertIn("render_video", hyperframes["owner_approval_required"])
        self.assertIn("publish", hyperframes["blocked"])
        self.assertEqual(agency["upstream"]["license"], "MIT")
        self.assertIn("fixed_slide_count", agency["not_adopted"])
        self.assertTrue((repository / agency["adaptation"]).exists())

    def test_current_runtime_adapter_blockers_are_explicit(self):
        console = AgentConsole(self.root, repository_root=Path.cwd())
        backends = console.snapshot()["capability_status"]["backends"]
        self.assertEqual(backends["claude_cli"]["status"], "available_on_demand")
        self.assertEqual(backends["spark"]["blocker"], "host_broker_not_verified")
        self.assertEqual(backends["codex"]["blocker"], "no_callable_adapter")
        self.assertEqual(backends["browser"]["blocker"], "app_only_no_local_callable_adapter")

    def test_verified_spark_host_receipt_does_not_claim_local_adapter(self):
        console = AgentConsole(self.root, repository_root=Path.cwd())
        console.record_backend_receipt(
            "spark",
            {
                "host_call_verified": True,
                "model": "gpt-5.3-codex-spark",
                "model_reasoning_summary": "none",
                "result": "reachable",
            },
        )
        reopened = AgentConsole(self.root, repository_root=Path.cwd())
        snapshot = reopened.snapshot()
        spark = snapshot["capability_status"]["backends"]["spark"]
        self.assertEqual(spark["status"], "host_broker_verified")
        self.assertEqual(spark["blocker"], "local_project_adapter_not_connected")
        self.assertFalse(snapshot["adapter_receipts"]["spark"]["local_project_adapter_connected"])
        self.assertTrue((self.root / "adapter_receipts" / "spark.json").exists())

    def test_observed_backend_status_survives_reopen(self):
        console = AgentConsole(self.root, repository_root=Path.cwd())
        console.set_backend_status(
            "claude_cli",
            {"status": "available", "mode": "create_one", "session_count": 0},
        )
        reopened = AgentConsole(self.root, repository_root=Path.cwd())
        self.assertEqual(
            reopened.snapshot()["capability_status"]["backends"]["claude_cli"]["status"],
            "available",
        )

    def test_single_claude_executor_dispatches_one_and_reconciles_receipt(self):
        class FakeClaude:
            def __init__(self):
                self.dispatched = []

            def availability(self):
                return {"status": "available", "mode": "create_one", "count": 0}

            def dispatch(self, *, job, context, handoff_path, dispatch_nonce, attempt):
                self.dispatched.append(job["job_id"])
                return {"status": "dispatched", "mode": "create_one", "session_id": "one"}

        console = AgentConsole(self.root)
        first = console.enqueue(title="first", category="news", context={"title": "A"})
        console.enqueue(title="second", category="story", context={"title": "B"})
        fake = FakeClaude()
        executor = AgentConsoleExecutor(console, fake)
        result = executor.run_once()
        self.assertEqual(result["dispatch"], first)
        self.assertEqual(fake.dispatched, [first])
        self.assertEqual(console._job(first)["status"], "running")
        inbox = console.handoff_dir / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        dispatch = console._job(first)["dispatch"]
        (inbox / f"{first}.json").write_text(
            json.dumps(
                {
                    "job_id": first,
                    "dispatch_nonce": dispatch["dispatch_nonce"],
                    "attempt": dispatch["attempt"],
                    "summary": "done",
                    "outputs": {"count": 1},
                    "warnings": [],
                }
            ),
            encoding="utf-8",
        )
        self.assertEqual(executor.reconcile(), [first])
        self.assertEqual(console._job(first)["status"], "completed")
        self.assertIn(CLAUDE_AGENT_ID, console._agents())

    def test_claude_reconcile_rejects_stale_attempt_receipt(self):
        class FakeClaude:
            def availability(self):
                return {"status": "available", "mode": "create_one", "count": 0}

            def dispatch(self, **kwargs):
                return {"status": "dispatched", "mode": "create_one", "session_id": "one"}

        console = AgentConsole(self.root)
        job_id = console.enqueue(title="strict", category="news", context={})
        executor = AgentConsoleExecutor(console, FakeClaude())
        executor.run_once()
        dispatch = console._job(job_id)["dispatch"]
        inbox = console.handoff_dir / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        receipt_path = inbox / f"{job_id}.json"
        receipt_path.write_text(
            json.dumps(
                {
                    "job_id": job_id,
                    "dispatch_nonce": "stale",
                    "attempt": dispatch["attempt"],
                    "summary": "late old result",
                    "outputs": {},
                    "warnings": [],
                }
            ),
            encoding="utf-8",
        )
        self.assertEqual(executor.reconcile(), [])
        self.assertEqual(console._job(job_id)["status"], "running")

    def test_claude_availability_counts_only_active_background_sessions(self):
        adapter = object.__new__(ClaudeCliAdapter)
        adapter.sessions = lambda: [
            {"id": "old", "sessionId": "old-session", "state": "done", "status": "idle", "startedAt": 1},
            {"id": "live", "sessionId": "live-session", "state": "working", "status": "busy", "startedAt": 2},
        ]
        status = adapter.availability()
        self.assertEqual(status["status"], "busy")
        self.assertEqual(status["session_id"], "live-session")


if __name__ == "__main__":
    unittest.main()
