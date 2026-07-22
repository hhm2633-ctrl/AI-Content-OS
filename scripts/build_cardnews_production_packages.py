"""Build CardNews planning packages from completed local handoffs.

This command writes JSON planning artifacts only.  It never renders, publishes,
issues affiliate links, resumes automation, or calls an external service.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.card_news.production_package_pipeline import (  # noqa: E402
    build_package_from_completed_handoff,
    normalize_completed_handoff,
)
from modules.agent_console.production_package_batch_bridge import (  # noqa: E402
    build_production_package_batch_inputs,
)
from modules.agent_console.package_completion_gate import (  # noqa: E402
    assess_package_completion,
)


DEFAULT_SELECTION = Path(
    "F:/AI-Content-OS-Data/source_intake/owner_ranked_final_selection_2026-07-19_fixed.json"
)
DEFAULT_STATE = REPO_ROOT / "artifacts" / "agent_console_v1" / "state.json"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "cardnews_production_packages"
INDEX_SCHEMA = "cardnews_production_package_index_v1"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _selection(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping) and isinstance(value.get("selection"), Mapping):
        return value["selection"]
    return value if isinstance(value, Mapping) else {}


def _selected(value: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    accounts = value.get("accounts")
    accounts = accounts if isinstance(accounts, Mapping) else {}
    for account in ("A", "B", "C"):
        bucket = accounts.get(account)
        selected = bucket.get("selected") if isinstance(bucket, Mapping) else []
        for raw in selected if isinstance(selected, list) else []:
            if not isinstance(raw, Mapping):
                continue
            candidate = dict(raw)
            candidate.setdefault("account", account)
            rows.append(candidate)
    return rows


def _completed_jobs(state: Any) -> Dict[str, Mapping[str, Any]]:
    jobs = state.get("jobs") if isinstance(state, Mapping) else []
    indexed: Dict[str, Mapping[str, Any]] = {}
    for job in jobs if isinstance(jobs, list) else []:
        if not isinstance(job, Mapping) or job.get("status") != "completed":
            continue
        candidate_id = str(job.get("candidate_id") or "").strip()
        handoff = job.get("handoff")
        if candidate_id and isinstance(handoff, Mapping) and candidate_id not in indexed:
            indexed[candidate_id] = handoff
    return indexed


def _approval_receipts(value: Any) -> Dict[str, Mapping[str, Any]]:
    rows = value.get("receipts") if isinstance(value, Mapping) else value
    if isinstance(rows, Mapping):
        rows = list(rows.values())
    indexed: Dict[str, Mapping[str, Any]] = {}
    for receipt in rows if isinstance(rows, list) else []:
        if not isinstance(receipt, Mapping):
            continue
        candidate_id = str(receipt.get("candidate_id") or "").strip()
        if candidate_id and candidate_id not in indexed:
            indexed[candidate_id] = receipt
    return indexed


def _blocked_package(candidate: Mapping[str, Any], reason: str) -> Dict[str, Any]:
    return {
        "schema_version": "selected_candidate_production_package_v1",
        "status": "blocked",
        "reason_code": reason,
        "candidate": {
            "candidate_id": str(candidate.get("candidate_id") or ""),
            "account": str(candidate.get("account") or "").upper(),
            "category": str(candidate.get("category") or ""),
            "title": str(candidate.get("title") or ""),
        },
        "missing_requirements": [reason],
        "story": {},
        "slides": [],
        "feed_caption": "",
        "media_plan": [],
        "gates": {
            "package_approval": {
                "status": "pending",
                "approved": False,
                "scope": "production_package",
                "reason_code": "package_approval_required",
            },
            "render": {"status": "blocked", "authorized": False},
            "publish": {"status": "blocked", "authorized": False},
        },
        "receipts": {
            "package_only": True,
            "render_executed": False,
            "publish_executed": False,
            "link_issuance_executed": False,
        },
    }


def _manifest_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def build_packages(
    selection_path: Path = DEFAULT_SELECTION,
    state_path: Path = DEFAULT_STATE,
    output_root: Path = DEFAULT_OUTPUT,
    approval_receipts_path: Path | None = None,
) -> Dict[str, Any]:
    final_selection = _selection(_load(selection_path))
    state = _load(state_path)
    candidates = _selected(final_selection)
    handoffs = _completed_jobs(state)
    approval_receipts = (
        _approval_receipts(_load(approval_receipts_path))
        if approval_receipts_path is not None
        else {}
    )
    candidate_index = {
        str(candidate.get("candidate_id") or ""): candidate for candidate in candidates
    }
    normalized_bundles = []
    for candidate_id, handoff in handoffs.items():
        candidate = candidate_index.get(candidate_id)
        if candidate is not None:
            normalized_bundles.append(
                normalize_completed_handoff(candidate, handoff)["deep_bundle"]
            )
    bridge = build_production_package_batch_inputs(
        final_selection, state, normalized_bundles
    )
    bridge_records = {
        record.get("candidate_id"): record
        for account in bridge.get("accounts", {}).values()
        for record in account.get("records", [])
        if isinstance(record, Mapping) and record.get("candidate_id")
    }
    output_root.mkdir(parents=True, exist_ok=True)
    entries: List[Dict[str, Any]] = []

    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id") or "").strip()
        handoff = handoffs.get(candidate_id)
        bridge_record = bridge_records.get(candidate_id, {})
        if bridge_record.get("status") != "ready" or handoff is None:
            package = _blocked_package(
                candidate,
                str(bridge_record.get("reason_code") or "completed_agent_handoff_missing"),
            )
        else:
            receipt = approval_receipts.get(candidate_id)
            result = build_package_from_completed_handoff(candidate, handoff, receipt)
            package = result["package"]
            if package.get("status") != "production_package_ready":
                package["missing_requirements"] = [
                    str(package.get("reason_code") or "production_package_incomplete")
                ]

        completion = assess_package_completion(package)
        package["completion_receipt"] = completion
        if not completion["package_complete"]:
            if package.get("status") != "production_package_pending_approval":
                package["status"] = "blocked"
            existing = package.get("missing_requirements")
            existing = existing if isinstance(existing, list) else []
            package["missing_requirements"] = list(
                dict.fromkeys(
                    [str(item) for item in existing if str(item).strip()]
                    + [
                        str(item.get("reason_code"))
                        for item in completion["missing_field_receipts"]
                        if item.get("reason_code")
                    ]
                )
            )

        package_id = f"cardnews-package:{candidate_id}"
        package["package_id"] = package_id
        package_file = output_root / f"{candidate_id}.json"
        package_file.write_text(
            json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        entries.append(
            {
                "package_id": package_id,
                "candidate_id": candidate_id,
                "account": str(candidate.get("account") or "").upper(),
                "category": str(candidate.get("category") or ""),
                "status": package.get("status"),
                "missing_requirements": package.get("missing_requirements", []),
                "package_path": _manifest_path(package_file),
            }
        )

    ready = sum(item["status"] == "production_package_ready" for item in entries)
    pending = sum(item["status"] == "production_package_pending_approval" for item in entries)
    blocked = sum(item["status"] == "blocked" for item in entries)
    manifest = {
        "schema_version": INDEX_SCHEMA,
        "generated_at": datetime.now().astimezone().isoformat(),
        "status": "ready" if ready == len(entries) and entries else ("partial" if ready else ("pending" if pending else "blocked")),
        "package_count": len(entries),
        "ready_count": ready,
        "pending_count": pending,
        "blocked_count": blocked,
        "packages": entries,
        "approval_scope": "production_package",
        "completion_gate_schema": "agent_console_package_completion_gate_v1",
        "batch_bridge": {
            "schema_version": bridge.get("schema_version"),
            "status": bridge.get("status"),
            "reason_code": bridge.get("reason_code"),
            "selected_count": bridge.get("selected_count", 0),
            "ready_count": bridge.get("ready_count", 0),
            "blocked_count": bridge.get("blocked_count", 0),
        },
        "render_executed": False,
        "publish_executed": False,
        "link_issuance_executed": False,
    }
    (output_root / "latest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--approval-receipts", type=Path)
    args = parser.parse_args()
    manifest = build_packages(args.selection, args.state, args.output, args.approval_receipts)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
