"""Build approval-gated packages from explicit selected-flow and story files.

This bridge performs no discovery, rendering, publishing, link issuance, or
external call. Missing approval receipts leave valid packages pending.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from modules.card_news.selected_candidate_production_package import (
    build_selected_candidate_production_package,
)


def _mapping_index(value: Any, list_key: str) -> Dict[str, Mapping[str, Any]]:
    rows = value.get(list_key) if isinstance(value, Mapping) else value
    if isinstance(rows, Mapping):
        rows = list(rows.values())
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("candidate_id") or "").strip(): row
        for row in rows if isinstance(row, Mapping)
        if str(row.get("candidate_id") or "").strip()
    }


def build_packages_from_selected_flow(
    flow_payload: Any,
    story_payload: Any,
    approval_payload: Any = None,
) -> Dict[str, Any]:
    root = flow_payload.get("production_flow") if isinstance(flow_payload, Mapping) else None
    flow = root if isinstance(root, Mapping) else flow_payload
    if not isinstance(flow, Mapping):
        return {
            "status": "closed",
            "reason_code": "selected_flow_must_be_object",
            "package_count": 0,
            "packages": [],
            "render_executed": False,
            "publishing_executed": False,
        }
    plans = flow.get("production_plans")
    render_inputs = flow.get("render_inputs")
    if not isinstance(plans, list) or not isinstance(render_inputs, list):
        return {
            "status": "closed",
            "reason_code": "selected_flow_plans_and_render_inputs_required",
            "package_count": 0,
            "packages": [],
            "render_executed": False,
            "publishing_executed": False,
        }

    stories = _mapping_index(story_payload, "stories")
    approvals = _mapping_index(approval_payload, "receipts")
    render_by_candidate: Dict[str, Mapping[str, Any]] = {}
    for receipt in render_inputs:
        if not isinstance(receipt, Mapping):
            continue
        preserved = receipt.get("full_plan_preserved")
        candidate_id = str(
            receipt.get("candidate_id")
            or (preserved.get("candidate_id") if isinstance(preserved, Mapping) else "")
            or ""
        ).strip()
        if candidate_id and candidate_id not in render_by_candidate:
            render_by_candidate[candidate_id] = receipt

    packages = []
    for plan in plans:
        if not isinstance(plan, Mapping):
            continue
        candidate_id = str(plan.get("candidate_id") or "").strip()
        render_receipt = render_by_candidate.get(candidate_id)
        story = stories.get(candidate_id)
        if render_receipt is None or story is None:
            packages.append({
                "schema_version": "selected_candidate_production_package_v1",
                "status": "blocked",
                "reason_code": "matching_render_input_and_story_required",
                "candidate_id": candidate_id,
                "receipts": {"render_executed": False, "publish_executed": False},
            })
            continue
        packages.append(build_selected_candidate_production_package(
            plan,
            render_receipt,
            story,
            approvals.get(candidate_id),
        ))

    ready_count = sum(row.get("status") == "production_package_ready" for row in packages)
    pending_count = sum(row.get("status") == "production_package_pending_approval" for row in packages)
    blocked_count = sum(row.get("status") == "blocked" for row in packages)
    return {
        "schema_version": "selected_flow_production_package_batch_v1",
        "status": (
            "ready" if packages and ready_count == len(packages)
            else "pending" if packages and pending_count == len(packages)
            else "partial" if packages and (ready_count or pending_count)
            else "blocked"
        ),
        "reason_code": "packages_composed_without_execution" if packages else "no_production_plans",
        "package_count": len(packages),
        "ready_count": ready_count,
        "pending_count": pending_count,
        "blocked_count": blocked_count,
        "packages": packages,
        "render_executed": False,
        "publishing_executed": False,
        "link_issuance_executed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flow", type=Path, required=True)
    parser.add_argument("--stories", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--approval-receipts", type=Path)
    args = parser.parse_args()
    try:
        flow = json.loads(args.flow.read_text(encoding="utf-8"))
        stories = json.loads(args.stories.read_text(encoding="utf-8"))
        approvals = (
            json.loads(args.approval_receipts.read_text(encoding="utf-8"))
            if args.approval_receipts else None
        )
        result = build_packages_from_selected_flow(flow, stories, approvals)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        result = {
            "status": "closed",
            "reason_code": f"input_read_failed:{type(exc).__name__}",
            "package_count": 0,
            "packages": [],
            "render_executed": False,
            "publishing_executed": False,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "reason_code": result["reason_code"],
        "package_count": result["package_count"],
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"ready", "pending", "partial"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
