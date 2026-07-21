"""Runner for persisting collection gap report and implementation queue."""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from modules.source_intake.collection_gap_report import STATUS_OK
from modules.source_intake.collection_gap_report import build_collection_gap_report
from modules.source_intake.source_intake_schema import SOURCE_INTAKE_STORAGE_ROOT


def _coerce_today(today: Optional[Any]) -> str:
    if not today:
        return date.today().isoformat()
    if isinstance(today, str):
        return today
    if isinstance(today, (datetime, date)):
        return today.isoformat()
    return str(today)


def _write_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _infer_owner(source_id: str, status: str, skip_reason: Optional[Any] = None) -> str:
    lower_source_id = source_id.lower() if isinstance(source_id, str) else ""
    lower_skip_reason = (skip_reason or "").lower()
    if "workflow" in lower_source_id and "engine" in lower_source_id:
        return "Codex"
    if any(token in lower_source_id for token in ("html", "browser", "parser", "collector", "crawl", "fetch")):
        return "Claude"
    if any(token in lower_source_id for token in ("workflow", "engine")) and status == STATUS_OK:
        return "Codex"
    if any(token in lower_skip_reason for token in ("browser", "html", "parser", "collector")):
        return "Claude"
    if any(token in lower_source_id for token in ("contract", "config", "report")):
        return "Spark"
    return "Spark"


def _next_action(owner: str) -> str:
    if owner == "Claude":
        return "implement html/browser/collector path"
    if owner == "Codex":
        return "wire into WorkflowEngine integration"
    return "update contract/config and keep gap report stable"


def _build_queue(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    queue: List[Dict[str, Any]] = []
    for entry in report.get("recommended_implementation_order", []) or []:
        status = entry.get("status")
        if status == STATUS_OK:
            continue
        source_id = entry.get("source_id")
        if not isinstance(source_id, str):
            continue
        lane_impact = entry.get("lane_impact") or []
        owner = _infer_owner(source_id, str(status), entry.get("skip_reason"))
        rank = len(queue) + 1
        queue.append(
            {
                "rank": rank,
                "source_id": source_id,
                "status": status,
                "lane_impact": lane_impact,
                "recommended_owner": owner,
                "next_action": _next_action(owner),
            }
        )
    return queue


def run_collection_gap_report(
    collection_result_path: Optional[str] = None,
    today: Optional[Any] = None,
    output_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Build gap report and implementation queue from shallow collection result."""
    today_str = _coerce_today(today)
    base_root = output_root or SOURCE_INTAKE_STORAGE_ROOT
    target_dir = os.path.join(base_root, today_str)
    if not collection_result_path:
        collection_result_path = os.path.join(target_dir, "daily_shallow_collection.json")

    if not os.path.exists(collection_result_path):
        return {
            "status": "input_missing",
            "today": today_str,
            "collection_result_path": collection_result_path,
        }

    report = build_collection_gap_report(collection_result_path)
    queue = _build_queue(report)
    report_path = os.path.join(target_dir, "collection_gap_report.json")
    queue_path = os.path.join(target_dir, "collector_implementation_queue.json")

    _write_json(report_path, report)
    _write_json(queue_path, {"implementation_queue": queue})

    return {
        "status": "completed",
        "today": today_str,
        "collection_result_path": collection_result_path,
        "collection_gap_report_path": report_path,
        "collector_implementation_queue_path": queue_path,
        "implementation_queue": queue,
    }
