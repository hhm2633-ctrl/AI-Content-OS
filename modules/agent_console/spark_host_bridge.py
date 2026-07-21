"""Data-only bridge between Agent Console queue and Spark host execution envelopes."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from modules.agent_console.console import AgentConsole, Handoff
from modules.agent_console.contracts import sanitize_json
from modules.agent_console.execution_prompt_pack import build_execution_prompt_pack


SPARK_BRIDGE_SCHEMA = "agent_console_spark_host_bridge_v1"
SPARK_RECEIPT_SCHEMA = "spark_host_receipt_v1"
MODEL_REASONING_SUMMARY = "none"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _short(value: Any, *, max_len: int = 500) -> str:
    text = str(value).strip()
    return text[:max_len]


def _safe_payload(value: Any) -> Dict[str, Any]:
    cleaned = sanitize_json(value)
    if isinstance(cleaned, dict):
        return cleaned
    return {"value": cleaned}


def _hash_text(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)


def _read_json(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _coerce_path(candidate: str | Path, *, fallback_dir: Path) -> Path:
    resolved = Path(candidate).resolve()
    fallback = fallback_dir.resolve()
    if resolved != fallback and fallback not in resolved.parents:
        raise PermissionError("Spark bridge paths must stay inside the Agent Console root")
    return resolved


class SparkHostBridge:
    """Queue-side bridge used by a remote host Spark runner."""

    def __init__(
        self,
        console: AgentConsole,
        *,
        outbox_dir: str | Path,
        receipt_dir: str | Path,
    ) -> None:
        self.console = console
        self.outbox_dir = _coerce_path(outbox_dir, fallback_dir=console.root)
        self.receipt_dir = _coerce_path(receipt_dir, fallback_dir=console.root)

    @staticmethod
    def _prompt_block(job: Mapping[str, Any], context: Mapping[str, Any]) -> str:
        prompt_pack = build_execution_prompt_pack(job, context)
        payload = {
            "objective": "execute exactly one Agent Console queued job",
            "job_id": job.get("job_id"),
            "title": job.get("title"),
            "category": job.get("category"),
            "execution_prompt_pack": prompt_pack,
        }
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _running_dispatch(job: Mapping[str, Any]) -> bool:
        dispatch = job.get("dispatch")
        if not isinstance(dispatch, Mapping):
            return False
        metadata = dispatch.get("spark_host_bridge")
        return isinstance(metadata, Mapping) and metadata.get("host_call_status") == "enqueued"

    def _envelope_for(self, claim: Mapping[str, Any], *, model_reasoning_summary: str) -> Dict[str, Any]:
        job = claim["job"]
        context = _safe_payload(claim["context"])
        job_id = str(job["job_id"])
        envelope_id = f"{job_id}:{_hash_text(context)}"
        prompt = self._prompt_block(job, context)
        prompt_pack = build_execution_prompt_pack(job, context)
        return {
            "schema_version": SPARK_BRIDGE_SCHEMA,
            "envelope_id": envelope_id,
            "created_at": _utc_now(),
            "model_reasoning_summary": model_reasoning_summary,
            "backend": "spark",
            "status": "queued",
            "job": {
                "job_id": job_id,
                "title": job.get("title"),
                "category": job.get("category"),
            },
            "context": context,
            "prompt": prompt,
            "education_receipt": prompt_pack["education_receipt"],
            "prompt_sha256": _hash_text(prompt),
            "instructions": {
                "queue_id": "agent_console",
                "requires_receipt_to_complete": True,
                "max_local_dispatch": 1,
            },
        }

    def dispatch_one(self, *, agent_id: str, model_reasoning_summary: str = MODEL_REASONING_SUMMARY) -> Optional[Dict[str, Any]]:
        if model_reasoning_summary != MODEL_REASONING_SUMMARY:
            raise ValueError('model_reasoning_summary must be "none" for Spark bridge')
        profile = self.console._agents().get(agent_id)
        if not isinstance(profile, Mapping) or profile.get("backend") != "spark":
            raise PermissionError("Spark host bridge requires a registered Spark agent")
        if profile.get("model_reasoning_summary") != MODEL_REASONING_SUMMARY:
            raise PermissionError('Spark agent must require model_reasoning_summary="none"')

        claim = self.console.claim_next(agent_id)
        if claim is None:
            return None

        envelope = self._envelope_for(claim, model_reasoning_summary=model_reasoning_summary)
        job_id = str(claim["job"]["job_id"])
        envelope_path = self.outbox_dir / f"{job_id}.json"
        try:
            _write_json(envelope_path, envelope)
            self.console.record_dispatch(
                job_id,
                {
                    "spark_host_bridge": {
                        "host_call_status": "enqueued",
                        "envelope_schema": SPARK_BRIDGE_SCHEMA,
                        "envelope_id": envelope["envelope_id"],
                        "envelope_path": str(envelope_path),
                        "education_receipt": envelope["education_receipt"],
                        "dispatched_at": _utc_now(),
                    },
                },
            )
        except Exception:
            envelope_path.unlink(missing_ok=True)
            self.console.fail(job_id, "spark_envelope_write_failed", retryable=True)
            raise
        return envelope

    def _read_receipt(self, job_id: str) -> Optional[Mapping[str, Any]]:
        path = self.receipt_dir / f"{job_id}.json"
        if not path.exists():
            return None
        raw = _read_json(path)
        if not isinstance(raw, Mapping):
            return None
        return _safe_payload(raw)

    def _build_handoff(self, *, job_id: str, receipt: Mapping[str, Any]) -> Handoff:
        status = str(receipt.get("status") or "completed")
        outputs = _safe_payload(receipt.get("outputs", {}))
        summary = _short(receipt.get("summary") or f"Spark receipt status={status}")
        return Handoff(
            summary=summary,
            outputs={"spark_receipt": sanitize_json(dict(receipt),)},
            warnings=[str(item) for item in receipt.get("warnings", [])][:10],
        )

    def reconcile_receipts(self, *, only_job_id: Optional[str] = None) -> Dict[str, Any]:
        jobs = [job for job in self.console.snapshot()["jobs"] if job.get("status") == "running"]
        if only_job_id:
            jobs = [job for job in jobs if str(job.get("job_id")) == only_job_id]
            if not jobs:
                return {"status": "none", "reconciled_jobs": []}
        matched = [job for job in jobs if self._running_dispatch(job)]
        reconciled: List[str] = []

        for job in matched:
            job_id = str(job["job_id"])
            receipt = self._read_receipt(job_id)
            if receipt is None:
                continue
            dispatch = job.get("dispatch", {}).get("spark_host_bridge", {})
            if receipt.get("schema_version") != SPARK_RECEIPT_SCHEMA:
                raise ValueError("receipt schema_version does not match Spark host contract")
            if str(receipt.get("job_id") or "") != job_id:
                raise ValueError("receipt job_id does not match the running job")
            if receipt.get("envelope_id") != dispatch.get("envelope_id"):
                raise ValueError("receipt envelope_id does not match the dispatched envelope")
            if receipt.get("model_reasoning_summary") != MODEL_REASONING_SUMMARY:
                raise ValueError('receipt model_reasoning_summary must be "none"')
            if receipt.get("status") != "completed":
                self.console.fail(job_id, f"spark_task_failed:{receipt.get('status', 'unknown')}", retryable=False)
                reconciled.append(job_id)
                continue
            handoff = self._build_handoff(job_id=job_id, receipt=receipt)
            self.console.complete(job_id, handoff)
            reconciled.append(job_id)

        if only_job_id:
            status = "completed" if only_job_id in reconciled else "pending"
            return {"status": status, "reconciled_jobs": reconciled}
        return {"status": "completed" if reconciled else "pending", "reconciled_jobs": reconciled}
