"""Bounded Agent Console executor for one reusable Claude CLI session.

One invocation reconciles finished handoffs and dispatches at most one job. It
does not schedule itself, publish, issue affiliate links, or call Spark through
an unverified local path.
"""

from __future__ import annotations

import argparse
import json
import secrets
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping

from modules.agent_console.console import AgentConsole
from modules.agent_console.contracts import AgentLimits, AgentProfile, Handoff
from modules.agent_console.execution_prompt_pack import build_execution_prompt_pack


CLAUDE_AGENT_ID = "claude-single"
APPROVED_LOCAL_TOOLS = ("filesystem", "project_cli", "graphify", "hyperframes")


class ClaudeCliAdapter:
    """Inspect and reuse exactly one Claude background session."""

    def __init__(self, repository_root: str | Path, *, timeout_seconds: int = 20) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.executable = shutil.which("claude")
        self.timeout_seconds = timeout_seconds
        if not self.executable:
            raise RuntimeError("claude executable is not available")

    def _run(self, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self.executable, *arguments],
            cwd=self.repository_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout_seconds,
        )

    def sessions(self) -> list[dict[str, Any]]:
        result = self._run(["agents", "--json"])
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or "claude agents failed")[:1000])
        payload = json.loads(result.stdout or "[]")
        if not isinstance(payload, list):
            raise RuntimeError("claude agents returned a non-list payload")
        return [entry for entry in payload if isinstance(entry, dict)]

    def availability(self) -> dict[str, Any]:
        sessions = self.sessions()
        active_states = {"working", "busy", "running", "starting"}
        active = [
            session
            for session in sessions
            if str(session.get("state") or session.get("status") or "").lower() in active_states
        ]
        if len(active) > 1:
            return {"status": "blocked", "reason": "multiple_active_sessions", "count": len(active)}
        if active:
            session = active[0]
            return {
                "status": "busy",
                "mode": "reuse_one",
                "count": 1,
                "session_id": session.get("sessionId"),
                "agent_id": session.get("id"),
            }
        if not sessions:
            return {"status": "available", "mode": "create_one", "count": 0}
        session = max(sessions, key=lambda entry: int(entry.get("startedAt") or 0))
        return {
            "status": "available",
            "mode": "reuse_one",
            "count": 0,
            "session_id": session.get("sessionId"),
            "agent_id": session.get("id"),
        }

    def dispatch(
        self,
        *,
        job: Mapping[str, Any],
        context: Mapping[str, Any],
        handoff_path: Path,
        dispatch_nonce: str,
        attempt: int,
    ) -> dict[str, Any]:
        availability = self.availability()
        if availability["status"] != "available":
            return availability
        prompt_pack = build_execution_prompt_pack(job, context)
        prompt = self._prompt(
            job=job,
            context=context,
            handoff_path=handoff_path,
            dispatch_nonce=dispatch_nonce,
            attempt=attempt,
            prompt_pack=prompt_pack,
        )
        arguments = ["--bg"]
        if availability["mode"] == "reuse_one":
            session_id = str(availability.get("session_id") or "").strip()
            if not session_id:
                raise RuntimeError("reusable Claude session has no sessionId")
            arguments.extend(["--resume", session_id])
        else:
            arguments.extend(
                [
                    "--model",
                    "fable",
                    "--permission-mode",
                    "auto",
                    "--name",
                    "agent-console-claude",
                ]
            )
        result = self._run([*arguments, prompt])
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or "Claude dispatch failed")[:1500])
        return {
            "status": "dispatched",
            "mode": availability["mode"],
            "session_id": availability.get("session_id"),
            "stdout": result.stdout.strip()[:500],
            "education_receipt": prompt_pack["education_receipt"],
        }

    @staticmethod
    def _prompt(
        *,
        job: Mapping[str, Any],
        context: Mapping[str, Any],
        handoff_path: Path,
        dispatch_nonce: str,
        attempt: int,
        prompt_pack: Mapping[str, Any] | None = None,
    ) -> str:
        pack = dict(prompt_pack) if isinstance(prompt_pack, Mapping) else build_execution_prompt_pack(job, context)
        safe_context = json.dumps(pack, ensure_ascii=False, separators=(",", ":"))
        base = (
            "AI-Content-OS Agent Console 작업 1건이다. 저장소 전체를 탐색하지 마라. "
            f"job_id={job.get('job_id')}, category={job.get('category')}, title={job.get('title')}. "
            f"sanitized_context={safe_context}. "
            "공개된 자료의 읽기 조사와 짧은 기획만 허용한다. 게시, 링크 발급, Git, 자동화, "
            "Commerce/Shorts 확장, 공용 상태문서와 코드 수정은 금지한다. "
            "결과는 job_id, dispatch_nonce, attempt, summary(500자 이하), outputs, warnings 키를 가진 "
            f"JSON 객체로 작성한다. job_id={job.get('job_id')}, dispatch_nonce={dispatch_nonce}, "
            f"attempt={attempt} 값을 그대로 넣고 "
            f"다른 파일은 건드리지 말고 정확히 {handoff_path} 에만 저장하라."
        )
        return base


class AgentConsoleExecutor:
    """Reconcile completed files and dispatch at most one queued work order."""

    def __init__(self, console: AgentConsole, claude: ClaudeCliAdapter) -> None:
        self.console = console
        self.claude = claude
        self.inbox = console.handoff_dir / "inbox"

    def _ensure_claude_profile(self) -> None:
        agents = self.console._agents()
        if CLAUDE_AGENT_ID in agents:
            if tuple(agents[CLAUDE_AGENT_ID].get("allowed_tools", [])) != APPROVED_LOCAL_TOOLS:
                self.console.grant_agent_tools(CLAUDE_AGENT_ID, APPROVED_LOCAL_TOOLS)
            return
        self.console.register_agent(
            AgentProfile(
                CLAUDE_AGENT_ID,
                "all",
                "claude_cli",
                allowed_tools=APPROVED_LOCAL_TOOLS,
                session_key="single-reusable",
                limits=AgentLimits(max_steps=6, timeout_seconds=1800, max_retries=1),
            )
        )

    def reconcile(self) -> list[str]:
        completed: list[str] = []
        for job in self.console.snapshot().get("jobs", []):
            if job.get("status") != "running" or job.get("agent_id") != CLAUDE_AGENT_ID:
                continue
            path = self.inbox / f"{job['job_id']}.json"
            if not path.exists():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            dispatch = job.get("dispatch") if isinstance(job.get("dispatch"), Mapping) else {}
            if (
                str(payload.get("job_id") or "") != str(job["job_id"])
                or payload.get("dispatch_nonce") != dispatch.get("dispatch_nonce")
                or int(payload.get("attempt") or -1) != int(dispatch.get("attempt") or -2)
            ):
                continue
            self.console.complete(
                str(job["job_id"]),
                Handoff(
                    str(payload.get("summary") or "").strip(),
                    payload.get("outputs") if isinstance(payload.get("outputs"), dict) else {},
                    payload.get("warnings") if isinstance(payload.get("warnings"), list) else [],
                ),
            )
            completed.append(str(job["job_id"]))
        return completed

    def run_once(self) -> dict[str, Any]:
        self._ensure_claude_profile()
        reconciled = self.reconcile()
        availability = self.claude.availability()
        self.console.set_backend_status(
            "claude_cli",
            {
                "status": availability["status"],
                "mode": availability.get("mode"),
                "session_count": availability.get("count"),
                "reason": availability.get("reason"),
                "session_id": availability.get("session_id"),
            },
        )
        if availability["status"] != "available":
            return {"status": availability["status"], "reconciled": reconciled, "dispatch": None}
        claimed = self.console.claim_next(CLAUDE_AGENT_ID)
        if claimed is None:
            return {"status": "idle", "reconciled": reconciled, "dispatch": None}
        job = claimed["job"]
        handoff_path = (self.inbox / f"{job['job_id']}.json").resolve()
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        handoff_path.unlink(missing_ok=True)
        dispatch_nonce = secrets.token_hex(16)
        attempt = int(job.get("attempts") or 0)
        try:
            dispatch = self.claude.dispatch(
                job=job,
                context=claimed["context"],
                handoff_path=handoff_path,
                dispatch_nonce=dispatch_nonce,
                attempt=attempt,
            )
        except Exception as exc:
            self.console.fail(str(job["job_id"]), f"claude_dispatch_failed:{exc}", retryable=True)
            raise
        if dispatch.get("status") != "dispatched":
            self.console.fail(str(job["job_id"]), "claude_became_busy_before_dispatch", retryable=True)
            return {"status": dispatch.get("status"), "reconciled": reconciled, "dispatch": None}
        self.console.record_dispatch(
            str(job["job_id"]),
            {
                "backend": "claude_cli",
                "handoff_path": str(handoff_path),
                "dispatch_nonce": dispatch_nonce,
                "attempt": attempt,
                **dispatch,
            },
        )
        return {"status": "dispatched", "reconciled": reconciled, "dispatch": job["job_id"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one bounded Agent Console execution cycle")
    parser.add_argument("--root", default="artifacts/agent_console_v1")
    args = parser.parse_args()
    repository = Path.cwd().resolve()
    console = AgentConsole(repository / args.root, repository_root=repository)
    result = AgentConsoleExecutor(console, ClaudeCliAdapter(repository)).run_once()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["AgentConsoleExecutor", "ClaudeCliAdapter"]
