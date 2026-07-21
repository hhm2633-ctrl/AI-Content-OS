"""Automatic one-job Spark runner over the verified local Codex CLI path.

The runner keeps Spark ephemeral and summary-disabled, uses a read-only
sandbox, writes a bounded receipt, and lets ``SparkHostBridge`` perform the
existing strict receipt reconciliation.  It never publishes, renders, issues
affiliate links, or starts more than one job per invocation.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

from modules.agent_console.console import AgentConsole
from modules.agent_console.contracts import AgentLimits, AgentProfile, sanitize_json
from modules.agent_console.spark_host_bridge import (
    MODEL_REASONING_SUMMARY,
    SPARK_RECEIPT_SCHEMA,
    SparkHostBridge,
)


SPARK_AGENT_ID = "spark-single"
SPARK_MODEL = "gpt-5.3-codex-spark"
APPROVED_LOCAL_TOOLS = ("filesystem", "project_cli", "graphify", "hyperframes")


def _find_codex_cli() -> Path:
    candidates: list[Path] = []
    configured = os.environ.get("CODEX_CLI_PATH")
    if configured:
        candidates.append(Path(configured))
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.extend(
            sorted(
                Path(local_app_data).glob("OpenAI/Codex/bin/*/codex.exe"),
                key=lambda path: path.stat().st_mtime if path.exists() else 0,
                reverse=True,
            )
        )
    discovered = shutil.which("codex")
    if discovered:
        candidates.append(Path(discovered))
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise RuntimeError("a callable Codex CLI was not found")


class SparkCodexCliAdapter:
    """Invoke Spark through Codex CLI with the required summary-disabled mode."""

    def __init__(self, repository_root: str | Path, *, timeout_seconds: int = 600) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.executable = _find_codex_cli()
        self.timeout_seconds = timeout_seconds

    def availability(self) -> dict[str, Any]:
        try:
            result = subprocess.run(
                [str(self.executable), "--version"],
                cwd=self.repository_root,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return {"status": "blocked", "reason": f"codex_cli_unavailable:{exc.__class__.__name__}"}
        if result.returncode != 0:
            return {"status": "blocked", "reason": "codex_cli_version_failed"}
        return {
            "status": "available",
            "model": SPARK_MODEL,
            "model_reasoning_summary": MODEL_REASONING_SUMMARY,
            "cli": (result.stdout or result.stderr).strip()[:200],
            "executable": str(self.executable),
        }

    @staticmethod
    def _schema() -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["summary", "outputs", "warnings"],
            "properties": {
                "summary": {"type": "string", "minLength": 1, "maxLength": 500},
                "outputs": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "brief": {"type": "string"},
                        "source_notes": {
                            "type": "array",
                            "maxItems": 10,
                            "items": {"type": "string"},
                        },
                        "cardnews_direction": {"type": "string"},
                        "caption_draft": {"type": "string"},
                    },
                    "required": ["brief", "source_notes", "cardnews_direction", "caption_draft"],
                },
                "warnings": {"type": "array", "maxItems": 10, "items": {"type": "string"}},
            },
        }

    def execute(self, envelope: Mapping[str, Any], *, runtime_dir: str | Path) -> dict[str, Any]:
        if envelope.get("model_reasoning_summary") != MODEL_REASONING_SUMMARY:
            raise ValueError('Spark envelope requires model_reasoning_summary="none"')
        runtime = Path(runtime_dir).resolve()
        runtime.mkdir(parents=True, exist_ok=True)
        schema_path = runtime / "spark_output_schema.json"
        schema_path.write_text(json.dumps(self._schema(), ensure_ascii=False), encoding="utf-8")
        handle, output_name = tempfile.mkstemp(prefix="spark-last-", suffix=".json", dir=runtime)
        os.close(handle)
        output_path = Path(output_name)
        prompt = (
            "다음 Agent Console 작업 1건만 수행하라. 제공된 후보와 교육 묶음만 사용하고 저장소 전체를 "
            "탐색하지 마라. 게시·링크 발급·Git·자동화·렌더·파일 수정은 금지한다. "
            "출력은 summary(500자 이하), outputs, warnings 키만 가진 JSON 객체여야 한다.\n"
            + str(envelope.get("prompt") or "")
        )
        command = [
            str(self.executable),
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--model",
            SPARK_MODEL,
            "-c",
            'model_reasoning_summary="none"',
            "-c",
            'approval_policy="never"',
            "--sandbox",
            "read-only",
            "--cd",
            str(self.repository_root),
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(output_path),
            prompt,
        ]
        try:
            result = subprocess.run(
                command,
                cwd=self.repository_root,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
            )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "Spark Codex CLI failed").strip()
                raise RuntimeError(detail[-2000:])
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or not str(payload.get("summary") or "").strip():
                raise RuntimeError("Spark returned an invalid bounded result")
            usage_match = re.search(r"tokens used\s+([0-9,]+)", result.stdout or "", re.IGNORECASE)
            return {
                "schema_version": SPARK_RECEIPT_SCHEMA,
                "status": "completed",
                "model": SPARK_MODEL,
                "model_reasoning_summary": MODEL_REASONING_SUMMARY,
                "job_id": envelope.get("job", {}).get("job_id"),
                "envelope_id": envelope.get("envelope_id"),
                "summary": str(payload["summary"]).strip()[:500],
                "outputs": sanitize_json(payload.get("outputs", {})),
                "warnings": [str(item)[:300] for item in payload.get("warnings", [])[:10]],
                "execution_receipt": {
                    "sandbox": "read-only",
                    "ephemeral": True,
                    "model_reasoning_summary": MODEL_REASONING_SUMMARY,
                    "cli_exit_code": result.returncode,
                    "reported_tokens_used": (
                        int(usage_match.group(1).replace(",", "")) if usage_match else None
                    ),
                },
            }
        finally:
            output_path.unlink(missing_ok=True)


class SparkAgentConsoleExecutor:
    """Claim, execute, receipt, and reconcile at most one Spark job."""

    def __init__(self, console: AgentConsole, adapter: SparkCodexCliAdapter) -> None:
        self.console = console
        self.adapter = adapter
        self.outbox = console.root / "spark_host" / "outbox"
        self.receipts = console.root / "spark_host" / "receipts"
        self.runtime = console.root / "spark_host" / "runtime"
        self.bridge = SparkHostBridge(console, outbox_dir=self.outbox, receipt_dir=self.receipts)

    def _ensure_profile(self) -> None:
        agents = self.console._agents()
        if SPARK_AGENT_ID in agents:
            self.console.grant_agent_tools(SPARK_AGENT_ID, APPROVED_LOCAL_TOOLS)
            return
        self.console.register_agent(
            AgentProfile(
                SPARK_AGENT_ID,
                "all",
                "spark",
                allowed_tools=APPROVED_LOCAL_TOOLS,
                limits=AgentLimits(max_steps=6, timeout_seconds=600, max_retries=1),
                model_reasoning_summary=MODEL_REASONING_SUMMARY,
            )
        )

    def _write_receipt(self, receipt: Mapping[str, Any]) -> Path:
        job_id = str(receipt.get("job_id") or "").strip()
        if not job_id:
            raise ValueError("Spark receipt has no job_id")
        path = self.receipts / f"{job_id}.json"
        self.console._atomic_write_json(path, receipt)
        return path

    def run_once(self) -> dict[str, Any]:
        self._ensure_profile()
        prior = self.bridge.reconcile_receipts()
        availability = self.adapter.availability()
        self.console.set_backend_status(
            "spark",
            {
                **availability,
                "adapter": "local_codex_cli",
                "model_reasoning_summary": MODEL_REASONING_SUMMARY,
            },
        )
        if availability.get("status") != "available":
            return {"status": "blocked", "prior_reconciliation": prior, "availability": availability}
        envelope = self.bridge.dispatch_one(
            agent_id=SPARK_AGENT_ID,
            model_reasoning_summary=MODEL_REASONING_SUMMARY,
        )
        if envelope is None:
            return {"status": "idle", "prior_reconciliation": prior, "availability": availability}
        job_id = str(envelope["job"]["job_id"])
        try:
            receipt = self.adapter.execute(envelope, runtime_dir=self.runtime)
            receipt_path = self._write_receipt(receipt)
            reconciliation = self.bridge.reconcile_receipts(only_job_id=job_id)
        except Exception as exc:
            self.console.fail(job_id, f"spark_cli_execution_failed:{exc}", retryable=True)
            raise
        return {
            "status": reconciliation["status"],
            "job_id": job_id,
            "receipt_path": str(receipt_path),
            "reconciliation": reconciliation,
            "availability": availability,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one automatic Spark Agent Console cycle")
    parser.add_argument("--root", default="artifacts/agent_console_v1")
    args = parser.parse_args()
    repository = Path.cwd().resolve()
    console = AgentConsole(repository / args.root, repository_root=repository)
    result = SparkAgentConsoleExecutor(console, SparkCodexCliAdapter(repository)).run_once()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["SparkAgentConsoleExecutor", "SparkCodexCliAdapter"]
