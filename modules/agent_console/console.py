"""Persistent local queue/chain coordinator for category work orders."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from hashlib import sha256
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from modules.agent_console.contracts import (
    AgentProfile,
    Handoff,
    JOB_STATUSES,
    sanitize_json,
)
from modules.agent_console.dashboard import render_dashboard
from modules.agent_console.tool_manifest import (
    LazyToolRegistry,
    ToolSpec,
    build_default_tool_registry,
)
from modules.agent_console.tool_assignment_policy import KNOWN_ASSIGNABLE_TOOLS


SCHEMA_VERSION = "agent_console_v1"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class AgentConsole:
    """Manage queue state without launching or pretending to launch an AI backend."""

    def __init__(
        self,
        root: str | Path,
        tools: LazyToolRegistry | None = None,
        *,
        repository_root: str | Path | None = None,
    ) -> None:
        self.root = Path(root)
        self.repository_root = Path(repository_root or Path.cwd()).resolve()
        self.state_path = self.root / "state.json"
        self.dashboard_path = self.root / "index.html"
        self.context_dir = self.root / "contexts"
        self.handoff_dir = self.root / "handoffs"
        self.adapter_receipt_dir = self.root / "adapter_receipts"
        self.tools = tools or build_default_tool_registry(self.repository_root)
        self._state = self._load_state()

    def _blank_state(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "updated_at": _iso(_utc_now()),
            "agents": [],
            "jobs": [],
            "tool_manifest": self.tools.manifest(),
            "capability_status": {
                "queue_chain": "available",
                "json_handoff": "available",
                "local_dashboard": "available",
                "external_agent_adapters": "not_connected",
                "backends": {
                    "codex": {
                        "status": "blocked",
                        "blocker": "no_callable_adapter",
                        "reason": "Codex app executable exists but access is denied from the local project process",
                    },
                    "claude_cli": {
                        "status": "available_on_demand",
                        "mode": "create_or_reuse_exactly_one_background_session",
                        "reason": "executor probes active sessions before each bounded dispatch",
                    },
                    "spark": {
                        "status": "blocked",
                        "blocker": "host_broker_not_verified",
                        "reason": "no verified host-broker receipt exists for model_reasoning_summary=none",
                    },
                    "browser": {
                        "status": "blocked",
                        "blocker": "app_only_no_local_callable_adapter",
                        "reason": "the read-only browser is app-only and has no local Python adapter",
                    },
                },
                "publishing": "blocked",
            },
        }

    def _load_state(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            return self._blank_state()
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._blank_state()
        if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
            return self._blank_state()
        payload["tool_manifest"] = self.tools.manifest()
        default_capabilities = self._blank_state()["capability_status"]
        capabilities = payload.setdefault("capability_status", {})
        for key, value in default_capabilities.items():
            capabilities.setdefault(key, value)
        backends = capabilities.setdefault("backends", {})
        for backend, default_status in default_capabilities["backends"].items():
            backends.setdefault(backend, default_status)
        self._apply_backend_receipts(payload)
        return payload

    def _apply_backend_receipts(self, state: Dict[str, Any]) -> None:
        """Apply verified host receipts without pretending a local adapter exists."""

        receipts = state.get("adapter_receipts")
        if not isinstance(receipts, Mapping):
            return
        spark = receipts.get("spark")
        if not isinstance(spark, Mapping):
            return
        if spark.get("host_call_verified") is not True:
            return
        if spark.get("model_reasoning_summary") != "none":
            return
        state["capability_status"]["backends"]["spark"] = {
            "status": "host_broker_verified",
            "blocker": "local_project_adapter_not_connected",
            "reason": (
                "the host broker successfully invoked Spark with model_reasoning_summary=none; "
                "the local Python process still cannot call that host broker directly"
            ),
            "model": spark.get("model"),
            "verified_at": spark.get("verified_at"),
        }
        state["capability_status"]["external_agent_adapters"] = "host_broker_verified"

    def _atomic_write_json(self, path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2)
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def _save(self) -> None:
        self._state["updated_at"] = _iso(_utc_now())
        self._state["tool_manifest"] = self.tools.manifest()
        self._atomic_write_json(self.state_path, self._state)
        render_dashboard(self._state, self.dashboard_path)

    def record_backend_receipt(self, backend: str, receipt: Mapping[str, Any]) -> Dict[str, Any]:
        """Persist a host-side adapter result as evidence, never as a local runner claim."""

        if backend != "spark":
            raise ValueError(f"unsupported backend receipt: {backend}")
        clean = sanitize_json(receipt)
        if not isinstance(clean, dict):
            raise ValueError("receipt must be a JSON object")
        if clean.get("host_call_verified") is not True:
            raise ValueError("Spark receipt requires host_call_verified=true")
        if clean.get("model_reasoning_summary") != "none":
            raise ValueError('Spark receipt requires model_reasoning_summary="none"')
        clean.setdefault("verified_at", _iso(_utc_now()))
        clean["backend"] = backend
        clean["local_project_adapter_connected"] = False
        self._state.setdefault("adapter_receipts", {})[backend] = clean
        self._apply_backend_receipts(self._state)
        self._atomic_write_json(self.adapter_receipt_dir / f"{backend}.json", clean)
        self._save()
        return dict(clean)

    def _agents(self) -> Dict[str, Dict[str, Any]]:
        return {entry["agent_id"]: entry for entry in self._state["agents"]}

    def _job(self, job_id: str) -> Dict[str, Any]:
        for job in self._state["jobs"]:
            if job.get("job_id") == job_id:
                return job
        raise KeyError(f"unknown job: {job_id}")

    def register_agent(self, profile: AgentProfile) -> None:
        agents = self._agents()
        if profile.agent_id in agents:
            raise ValueError(f"agent already registered: {profile.agent_id}")
        if profile.backend == "claude_cli":
            claude_profiles = [item for item in agents.values() if item.get("backend") == "claude_cli"]
            if claude_profiles:
                raise ValueError("only one reusable Claude CLI profile is allowed")
        unknown_tools = set(profile.allowed_tools) - set(self.tools.manifest())
        if unknown_tools:
            raise ValueError(f"unknown allowed tools: {sorted(unknown_tools)}")
        self._state["agents"].append(profile.to_dict())
        self._save()

    def grant_agent_tools(self, agent_id: str, allowed_tools: Iterable[str]) -> Dict[str, Any]:
        """Replace one agent's allow-list with registered, non-publishing tools."""

        agent = self._agents().get(agent_id)
        if agent is None:
            raise KeyError(f"unknown agent: {agent_id}")
        tools = list(dict.fromkeys(str(item).strip() for item in allowed_tools if str(item).strip()))
        unknown = set(tools) - set(self.tools.manifest())
        if unknown:
            raise ValueError(f"unknown allowed tools: {sorted(unknown)}")
        forbidden = set(tools) - set(KNOWN_ASSIGNABLE_TOOLS)
        if forbidden:
            raise ValueError(f"tools are not assignable: {sorted(forbidden)}")
        agent["allowed_tools"] = tools
        self._save()
        return dict(agent)

    def enqueue(
        self,
        *,
        title: str,
        category: str,
        context: Mapping[str, Any],
        depends_on: Iterable[str] = (),
        requested_tools: Iterable[str] = (),
        job_id: Optional[str] = None,
    ) -> str:
        if category not in {"news", "story", "fashion", "beauty"}:
            raise ValueError(f"unsupported category: {category}")
        if not title.strip():
            raise ValueError("title is required")
        resolved_id = job_id or f"job-{uuid.uuid4().hex[:12]}"
        if any(job.get("job_id") == resolved_id for job in self._state["jobs"]):
            raise ValueError(f"job already exists: {resolved_id}")
        dependencies = list(dict.fromkeys(str(item) for item in depends_on))
        known_jobs = {job.get("job_id") for job in self._state["jobs"]}
        missing = [item for item in dependencies if item not in known_jobs]
        if missing:
            raise ValueError(f"unknown dependencies: {missing}")
        tools = list(dict.fromkeys(str(item) for item in requested_tools))
        if set(tools) - set(self.tools.manifest()):
            raise ValueError("requested_tools contains an unknown tool")
        sanitized = sanitize_json(context)
        context_path = self.context_dir / f"{resolved_id}.json"
        self._atomic_write_json(context_path, sanitized if isinstance(sanitized, dict) else {"value": sanitized})
        self._state["jobs"].append(
            {
                "job_id": resolved_id,
                "title": title.strip(),
                "category": category,
                "status": "queued",
                "depends_on": dependencies,
                "requested_tools": tools,
                "context_path": str(context_path),
                "agent_id": None,
                "attempts": 0,
                "steps_used": 0,
                "max_steps": None,
                "queued_at": _iso(_utc_now()),
                "started_at": None,
                "deadline_at": None,
                "finished_at": None,
                "last_error": None,
                "handoff": None,
            }
        )
        self._save()
        return resolved_id

    def enqueue_category_chain(
        self,
        contexts: Mapping[str, Mapping[str, Any]],
        *,
        sequential: bool = False,
    ) -> List[str]:
        """Create four category jobs; no dependencies means they can run in parallel."""

        created: List[str] = []
        previous: Optional[str] = None
        for category in ("news", "story", "fashion", "beauty"):
            if category not in contexts:
                continue
            dependencies = [previous] if sequential and previous else []
            current = self.enqueue(
                title=f"{category} category task",
                category=category,
                context=contexts[category],
                depends_on=dependencies,
            )
            created.append(current)
            previous = current
        return created

    def sync_owner_review_queue(self, queue: Mapping[str, Any]) -> Dict[str, int]:
        """Mirror the persistent owner-review queue into local orchestration jobs.

        Owner grades are learning/selection input, not execution approval. New
        and re-opened records stay outside the executable queue until an
        explicit second-stage promotion. Completed/running work is preserved.
        """

        if queue.get("schema_version") != "owner_ranked_deep_dive_queue_v1":
            raise ValueError("unsupported owner-review queue schema")
        raw_requests = queue.get("requests")
        if not isinstance(raw_requests, list):
            raise ValueError("owner-review queue requests must be a list")

        by_source = {
            str(job.get("source_request_id")): job
            for job in self._state["jobs"]
            if job.get("source") == "owner_review" and job.get("source_request_id")
        }
        active_ids: set[str] = set()
        counters = {"created": 0, "updated": 0, "cancelled": 0}
        for request in raw_requests:
            if not isinstance(request, Mapping):
                continue
            source_request_id = str(request.get("request_id") or "").strip()
            candidate_id = str(request.get("candidate_id") or "").strip()
            if not source_request_id or not candidate_id:
                continue
            active_ids.add(source_request_id)
            category = self._owner_review_category(request)
            title = str(request.get("title") or candidate_id).strip()
            context = sanitize_json(
                {
                    "source": "owner_review",
                    "request_id": source_request_id,
                    "candidate_id": candidate_id,
                    "grade": request.get("grade"),
                    "account": request.get("account"),
                    "category": request.get("category"),
                    "title": title,
                    "source_urls": request.get("source_urls", []),
                    "requested_media": request.get("requested_media", []),
                    "execution_enabled": False,
                    "network_executed": False,
                }
            )
            current = by_source.get(source_request_id)
            if current is None:
                job_id = f"owner-review-{sha256(source_request_id.encode('utf-8')).hexdigest()[:16]}"
                context_path = self.context_dir / f"{job_id}.json"
                self._atomic_write_json(context_path, context)
                self._state["jobs"].append(
                    {
                        "job_id": job_id,
                        "title": title,
                        "category": category,
                        "status": "awaiting_second_stage",
                        "depends_on": [],
                        "requested_tools": [],
                        "context_path": str(context_path),
                        "agent_id": None,
                        "attempts": 0,
                        "steps_used": 0,
                        "max_steps": None,
                        "queued_at": _iso(_utc_now()),
                        "started_at": None,
                        "deadline_at": None,
                        "finished_at": None,
                        "last_error": None,
                        "handoff": None,
                        "source": "owner_review",
                        "source_request_id": source_request_id,
                        "candidate_id": candidate_id,
                        "execution_approved": False,
                        "execution_adapter": "not_connected",
                    }
                )
                counters["created"] += 1
                continue

            current.update({"title": title, "category": category, "candidate_id": candidate_id})
            self._atomic_write_json(Path(current["context_path"]), context)
            if current.get("status") == "cancelled":
                current.update(
                    {
                        "status": "awaiting_second_stage",
                        "finished_at": None,
                        "last_error": None,
                    }
                )
            counters["updated"] += 1

        for source_request_id, job in by_source.items():
            if source_request_id in active_ids or job.get("status") in {"running", "completed"}:
                continue
            if job.get("status") != "cancelled":
                job.update(
                    {
                        "status": "cancelled",
                        "finished_at": _iso(_utc_now()),
                        "last_error": "removed_from_owner_review_queue",
                    }
                )
                counters["cancelled"] += 1

        self._state["owner_review_sync"] = {
            "source_schema": queue.get("schema_version"),
            "source_updated_at": queue.get("updated_at"),
            "synced_at": _iso(_utc_now()),
            "active_request_count": len(active_ids),
            **counters,
        }
        self._save()
        return counters

    def hold_unselected_owner_review_jobs(self) -> List[str]:
        """Remove unapproved owner-review candidates from the executable queue.

        This is an idempotent migration for states created before the explicit
        second-stage gate existed. Running/completed records are never changed.
        """

        held: List[str] = []
        for job in self._state["jobs"]:
            if job.get("source") != "owner_review" or job.get("status") != "queued":
                continue
            context_path = Path(str(job.get("context_path") or ""))
            try:
                context = json.loads(context_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                context = {}
            if context.get("execution_enabled") is True:
                continue
            job.update(
                {
                    "status": "awaiting_second_stage",
                    "execution_approved": False,
                    "agent_id": None,
                    "deadline_at": None,
                    "last_error": None,
                }
            )
            held.append(str(job["job_id"]))
        if held:
            self._save()
        return held

    def promote_owner_review_jobs(self, source_request_ids: Iterable[str]) -> List[str]:
        """Explicitly promote final second-stage selections for execution."""

        requested = {str(item).strip() for item in source_request_ids if str(item).strip()}
        promoted: List[str] = []
        for job in self._state["jobs"]:
            if (
                job.get("source") != "owner_review"
                or job.get("source_request_id") not in requested
                or job.get("status") != "awaiting_second_stage"
            ):
                continue
            context_path = Path(str(job["context_path"]))
            context = json.loads(context_path.read_text(encoding="utf-8"))
            context["execution_enabled"] = True
            context["selection_stage"] = "final_selected"
            self._atomic_write_json(context_path, context)
            job.update(
                {
                    "status": "queued",
                    "execution_approved": True,
                    "queued_at": _iso(_utc_now()),
                    "finished_at": None,
                    "last_error": None,
                }
            )
            promoted.append(str(job["job_id"]))
        if promoted:
            self._save()
        return promoted

    def reconcile_owner_review_selection(self, source_request_ids: Iterable[str]) -> Dict[str, List[str]]:
        """Make the latest final selection executable and hold every other pending review job.

        Running and completed history is immutable. This only changes pending
        owner-review work and is safe to call repeatedly with the same set.
        """

        selected = {str(item).strip() for item in source_request_ids if str(item).strip()}
        promoted: List[str] = []
        held: List[str] = []
        unchanged_history: List[str] = []
        for job in self._state["jobs"]:
            if job.get("source") != "owner_review":
                continue
            if job.get("status") in {"running", "completed"}:
                unchanged_history.append(str(job["job_id"]))
                continue
            is_selected = str(job.get("source_request_id") or "") in selected
            context_path = Path(str(job.get("context_path") or ""))
            try:
                context = json.loads(context_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                context = {}
            context["execution_enabled"] = is_selected
            context["selection_stage"] = "final_selected" if is_selected else "awaiting_second_stage"
            self._atomic_write_json(context_path, context)
            if is_selected:
                if job.get("status") != "queued" or job.get("execution_approved") is not True:
                    promoted.append(str(job["job_id"]))
                job.update(
                    {
                        "status": "queued",
                        "execution_approved": True,
                        "queued_at": _iso(_utc_now()),
                        "finished_at": None,
                        "last_error": None,
                    }
                )
            else:
                if job.get("status") != "awaiting_second_stage" or job.get("execution_approved") is not False:
                    held.append(str(job["job_id"]))
                job.update(
                    {
                        "status": "awaiting_second_stage",
                        "execution_approved": False,
                        "agent_id": None,
                        "deadline_at": None,
                        "finished_at": None,
                        "last_error": None,
                    }
                )
        self._save()
        return {"promoted": promoted, "held": held, "unchanged_history": unchanged_history}

    @staticmethod
    def _owner_review_category(request: Mapping[str, Any]) -> str:
        account = str(request.get("account") or "").upper()
        category = str(request.get("category") or "")
        if account == "A":
            return "news"
        if account == "B":
            return "story"
        if any(token in category.lower() for token in ("뷰티", "미용", "향수", "메이크업", "스킨", "헤어", "beauty")):
            return "beauty"
        return "fashion"

    def _dependencies_complete(self, job: Mapping[str, Any]) -> bool:
        by_id = {entry.get("job_id"): entry for entry in self._state["jobs"]}
        return all(by_id.get(job_id, {}).get("status") == "completed" for job_id in job.get("depends_on", []))

    def ready_jobs(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        self.sweep_timeouts(save=False)
        return [
            dict(job)
            for job in self._state["jobs"]
            if job.get("status") == "queued"
            and (job.get("source") != "owner_review" or job.get("execution_approved") is True)
            and (category is None or job.get("category") == category)
            and self._dependencies_complete(job)
        ]

    def claim_next(self, agent_id: str) -> Optional[Dict[str, Any]]:
        agents = self._agents()
        if agent_id not in agents:
            raise KeyError(f"unknown agent: {agent_id}")
        profile = agents[agent_id]
        if any(job.get("status") == "running" and job.get("agent_id") == agent_id for job in self._state["jobs"]):
            raise RuntimeError("agent already owns a running job")
        if profile.get("backend") == "claude_cli" and any(
            job.get("status") == "running"
            and self._agents().get(str(job.get("agent_id")), {}).get("backend") == "claude_cli"
            for job in self._state["jobs"]
        ):
            raise RuntimeError("the reusable Claude CLI session is already in use")
        ready = self.ready_jobs(category=None if profile["category"] == "all" else profile["category"])
        if not ready:
            return None
        job = self._job(ready[0]["job_id"])
        context = json.loads(Path(job["context_path"]).read_text(encoding="utf-8"))
        assignment = self.tools.assign_for_job(
            job,
            allowed_tools=profile.get("allowed_tools", []),
            requested_tools=job.get("requested_tools") or None,
            context=context,
        )
        requested = set(assignment.get("assigned_tools", []))
        allowed = set(profile.get("allowed_tools", []))
        if job.get("requested_tools") and assignment.get("status") != "assigned":
            job["status"] = "blocked"
            job["last_error"] = "tool_assignment_denied"
            job["tool_assignment"] = assignment
            self._save()
            return None
        if requested - allowed:
            job["status"] = "blocked"
            job["last_error"] = f"tool_not_allowed:{','.join(sorted(requested - allowed))}"
            self._save()
            return None
        job["requested_tools"] = list(assignment.get("assigned_tools", []))
        job["tool_assignment"] = assignment
        now = _utc_now()
        limits = profile["limits"]
        job.update(
            {
                "status": "running",
                "agent_id": agent_id,
                "attempts": int(job.get("attempts", 0)) + 1,
                "steps_used": 0,
                "max_steps": limits["max_steps"],
                "started_at": _iso(now),
                "deadline_at": _iso(now + timedelta(seconds=limits["timeout_seconds"])),
                "finished_at": None,
                "last_error": None,
            }
        )
        self._save()
        return {
            "job": dict(job),
            "context": context,
            "tools": self.tools.manifest(requested),
        }

    def record_dispatch(self, job_id: str, metadata: Mapping[str, Any]) -> Dict[str, Any]:
        """Attach sanitized executor metadata to a running work order."""

        job = self._job(job_id)
        if job.get("status") != "running":
            raise RuntimeError("dispatch metadata requires a running job")
        job["dispatch"] = sanitize_json(metadata)
        self._save()
        return dict(job)

    def set_backend_status(self, backend: str, status: Mapping[str, Any]) -> None:
        """Persist an observed runtime status without changing queued work."""

        backends = self._state.setdefault("capability_status", {}).setdefault("backends", {})
        if backend not in backends:
            raise ValueError(f"unknown backend: {backend}")
        backends[backend] = sanitize_json(status)
        self._save()

    def record_step(self, job_id: str, *, label: str = "") -> Dict[str, Any]:
        job = self._job(job_id)
        if job.get("status") != "running":
            raise RuntimeError("steps can only be recorded for a running job")
        if _utc_now() >= _parse_iso(job["deadline_at"]):
            self.fail(job_id, "time_limit_exceeded", retryable=True)
            raise TimeoutError("agent job exceeded its time limit")
        next_step = int(job.get("steps_used", 0)) + 1
        if next_step > int(job.get("max_steps", 0)):
            self.fail(job_id, "step_limit_exceeded", retryable=False)
            raise RuntimeError("agent job exceeded its step limit")
        job["steps_used"] = next_step
        job["last_step"] = str(label)[:200]
        self._save()
        return dict(job)

    def load_tool(self, job_id: str, tool_id: str) -> Any:
        job = self._job(job_id)
        if job.get("status") != "running":
            raise RuntimeError("tools can only be loaded for a running job")
        profile = self._agents()[str(job["agent_id"])]
        if tool_id not in set(job.get("requested_tools", [])):
            raise PermissionError(f"tool was not requested by job: {tool_id}")
        return self.tools.load(tool_id, profile.get("allowed_tools", []))

    def complete(self, job_id: str, handoff: Handoff) -> Dict[str, Any]:
        job = self._job(job_id)
        if job.get("status") != "running":
            raise RuntimeError("only a running job can complete")
        payload = handoff.to_dict()
        handoff_path = self.handoff_dir / f"{job_id}.json"
        self._atomic_write_json(handoff_path, payload)
        job.update(
            {
                "status": "completed",
                "finished_at": _iso(_utc_now()),
                "deadline_at": None,
                "handoff_path": str(handoff_path),
                "handoff": payload,
            }
        )
        self._save()
        return dict(job)

    def fail(self, job_id: str, reason: str, *, retryable: bool = True) -> Dict[str, Any]:
        job = self._job(job_id)
        profile = self._agents().get(str(job.get("agent_id")), {})
        retries = int(profile.get("limits", {}).get("max_retries", 0))
        can_retry = retryable and int(job.get("attempts", 0)) <= retries
        retry_status = "queued"
        if job.get("source") == "owner_review" and job.get("execution_approved") is not True:
            retry_status = "awaiting_second_stage"
        job.update(
            {
                "status": retry_status if can_retry else "failed",
                "finished_at": None if can_retry else _iso(_utc_now()),
                "deadline_at": None,
                "last_error": str(reason)[:500],
                "agent_id": None if can_retry else job.get("agent_id"),
            }
        )
        self._save()
        return dict(job)

    def sweep_timeouts(self, *, now: Optional[datetime] = None, save: bool = True) -> List[str]:
        current = now or _utc_now()
        timed_out: List[str] = []
        for job in list(self._state["jobs"]):
            deadline = job.get("deadline_at")
            if job.get("status") == "running" and deadline and current >= _parse_iso(deadline):
                timed_out.append(str(job["job_id"]))
                self.fail(str(job["job_id"]), "time_limit_exceeded", retryable=True)
        if timed_out and save:
            self._save()
        return timed_out

    def snapshot(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self._state, ensure_ascii=False))


__all__ = ["AgentConsole", "SCHEMA_VERSION", "ToolSpec"]
