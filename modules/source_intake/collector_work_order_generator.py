"""Generate Claude work-order markdowns from collector implementation queue."""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional


def _coerce_today(today: Optional[Any] = None) -> str:
    if not today:
        return date.today().isoformat()
    if isinstance(today, str):
        return today
    if isinstance(today, (datetime, date)):
        return today.isoformat()
    return str(today)


def _safe_token(value: Any) -> str:
    text = str(value or "").lower().strip()
    safe = re.sub(r"[^0-9a-zA-Z]+", "_", text)
    safe = safe.strip("_")
    return safe or "item"


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("collector queue payload must be an object")
    return payload


def _extract_queue(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    queue = payload.get("implementation_queue", [])
    if not isinstance(queue, list):
        raise ValueError("implementation_queue must be a list")
    return queue


def _work_order_markdown(queue_item: Dict[str, Any], source_id: str, status: str) -> str:
    lane_impact = queue_item.get("lane_impact") or []
    if not isinstance(lane_impact, list):
        lane_impact = []

    lanes = ", ".join(str(item) for item in lane_impact) or "not specified"
    return (
        "# Collector Work Order\n\n"
        "## objective\n"
        f"- implement the `{source_id}` collector path and wire source intake metadata for status `{status}`\n\n"
        "## owned files\n"
        f"- modules/trend_collector/{source_id}_collector.py when this source needs a new collector\n"
        "- modules/source_intake/source_capability_map.py only if capability metadata must be extended\n"
        f"- tests/test_{source_id}_collector.py or focused source-intake collector tests\n\n"
        "## prohibited files\n"
        "- modules/workflow_engine.py\n"
        "- modules/card_news\n"
        "- modules/publishing\n"
        "- modules/compliance\n"
        "- unrelated existing collectors\n\n"
        "## required reading\n"
        "- modules/source_intake/collection_gap_runner.py\n"
        "- collection gap queue item: source_id, status, lane_impact\n"
        f"- affected lanes: {lanes}\n\n"
        "## completion checks\n"
        "- collector module can import and load without runtime crash\n"
        "- queue-related integration contract tests pass with this source id\n"
        "- new collector output shape matches existing source intake contract\n\n"
        "## handoff format\n"
        "- status: done\n"
        "- owner: Spark -> Claude\n"
        "- files_touched: comma-separated list\n"
        "- blockers: short bullet list\n"
        "- test result summary\n"
    )


def generate_collector_work_orders(
    queue_path: Optional[str] = None,
    today: Optional[Any] = None,
    output_dir: Optional[str] = None,
    max_orders: int = 3,
) -> Dict[str, Any]:
    """Create limited Claude work-order markdown files from a collector queue."""
    today_str = _coerce_today(today)
    resolved_queue_path = queue_path or os.path.join("storage", "source_intake", today_str, "collector_implementation_queue.json")
    resolved_output_dir = output_dir or os.path.join("external_workclaude", "source_collector_work_orders", today_str)

    if not os.path.exists(resolved_queue_path):
        return {
            "status": "input_missing",
            "today": today_str,
            "queue_path": resolved_queue_path,
        }

    try:
        payload = _read_json(resolved_queue_path)
        queue = _extract_queue(payload)
    except Exception as exc:  # pragma: no cover - defensive branch, covered by tests if desired
        return {
            "status": "input_error",
            "today": today_str,
            "queue_path": resolved_queue_path,
            "error": f"{type(exc).__name__}: {exc}",
        }

    clauded = [
        item for item in queue
        if isinstance(item, dict) and item.get("recommended_owner") == "Claude"
    ]
    def _rank_key(item: Dict[str, Any]) -> int:
        rank = item.get("rank")
        return int(rank) if isinstance(rank, int) else 10**9

    clauded.sort(key=_rank_key)
    selected = clauded[: max(0, int(max_orders))]

    if not selected:
        return {
            "status": "no_eligible_items",
            "today": today_str,
            "queue_path": resolved_queue_path,
            "output_dir": resolved_output_dir,
            "generated_count": 0,
            "generated_files": [],
        }

    os.makedirs(resolved_output_dir, exist_ok=True)
    written: List[str] = []

    for item in selected:
        source_id = str(item.get("source_id", "unknown"))
        status = str(item.get("status", "unknown"))
        rank = item.get("rank", "000")
        safe_name = f"{_safe_token(source_id)}_{_safe_token(status)}_{_safe_token(rank)}.md"
        file_path = os.path.join(resolved_output_dir, safe_name)
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(_work_order_markdown(item, source_id, status))
        written.append(file_path)

    return {
        "status": "completed",
        "today": today_str,
        "queue_path": resolved_queue_path,
        "output_dir": resolved_output_dir,
        "generated_count": len(written),
        "generated_files": written,
    }
