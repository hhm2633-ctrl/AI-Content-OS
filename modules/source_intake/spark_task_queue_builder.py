"""Build a deterministic, Spark-safe collector task queue."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from modules.source_intake.collection_gap_report import KNOWN_NEWS_PORTAL_IDS
from modules.source_intake.source_intake_schema import SOURCE_INTAKE_STORAGE_ROOT

SPARK_TASK_QUEUE_SCHEMA = "spark_task_queue_v1"
DEFAULT_QUEUE_PATH = os.path.join(SOURCE_INTAKE_STORAGE_ROOT, "2026-07-14", "collector_implementation_queue.json")
DEFAULT_OUTPUT_PATH = os.path.join(SOURCE_INTAKE_STORAGE_ROOT, "2026-07-14", "spark_task_queue.json")

_SPARK_OWNER = "spark"
_OK_STATUS = "OK"

_SPARK_SAFE_EXCLUDE_KEYWORDS = {
    "html",
    "browser",
    "browser_work",
    "browserwork",
    "parser",
    "collector",
    "crawl",
    "crawling",
    "selenium",
    "playwright",
    "credential",
    "credentialing",
    "publish",
    "publishing",
    "git",
    "github",
    "shared_doc",
    "shared_docs",
    "sharedocument",
    "doc",
    "docs",
    "documents",
}

_SPARK_ALLOWED_ACTION_HINTS = (
    "contract",
    "diagnostic",
    "test",
    "config",
    "schema",
    "contracts",
)


def _coerce_queue(payload: Any) -> List[Dict[str, Any]]:
    queue = payload.get("implementation_queue") if isinstance(payload, dict) else None
    if not isinstance(queue, list):
        return []
    return [entry for entry in queue if isinstance(entry, dict)]


def _is_claude_owner(entry: Dict[str, Any]) -> bool:
    owner = str(entry.get("recommended_owner", "")).lower()
    return owner.startswith("claude")

def _contains_blocked_keyword(source_id: str, next_action: str) -> bool:
    text = f"{source_id} {next_action}".lower()
    return any(block in text for block in _SPARK_SAFE_EXCLUDE_KEYWORDS)


def _is_task_candidate(entry: Dict[str, Any]) -> bool:
    owner = str(entry.get("recommended_owner", "")).lower()
    status = str(entry.get("status", "")).upper()
    source_id = str(entry.get("source_id", ""))
    next_action = str(entry.get("next_action", ""))

    if not source_id:
        return False
    if _is_claude_owner(entry):
        return False
    if status == _OK_STATUS:
        return False
    if owner != _SPARK_OWNER:
        return False
    if source_id.lower() in KNOWN_NEWS_PORTAL_IDS:
        return False
    if _contains_blocked_keyword(source_id, next_action):
        return False
    if any(token in next_action.lower() for token in _SPARK_ALLOWED_ACTION_HINTS):
        return True
    return True


def _build_spark_queue(queue: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    candidates = [entry for entry in queue if _is_task_candidate(entry)]
    candidates.sort(key=lambda item: (str(item.get("source_id", "")).lower(), str(item.get("rank", ""))))

    built: List[Dict[str, Any]] = []
    for index, entry in enumerate(candidates, start=1):
        built.append(
            {
                "rank": index,
                "source_id": entry.get("source_id"),
                "status": entry.get("status"),
                "lane_impact": entry.get("lane_impact") or [],
                "task_type": "diagnostic_contract",
            }
        )
    return built


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def run_spark_task_queue(
    queue_path: Optional[str] = None,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    resolved_input = queue_path or DEFAULT_QUEUE_PATH
    resolved_output = output_path or DEFAULT_OUTPUT_PATH

    if not os.path.exists(resolved_input):
        return {
            "status": "input_missing",
            "queue_path": resolved_input,
            "output_path": resolved_output,
        }

    payload = _read_json(resolved_input)
    queue_items = _coerce_queue(payload)
    spark_queue = _build_spark_queue(queue_items)
    result_payload = {
        "schema_version": SPARK_TASK_QUEUE_SCHEMA,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "queue_source": resolved_input,
        "task_count": len(spark_queue),
        "spark_task_queue": spark_queue,
    }
    _write_json(resolved_output, result_payload)

    return {
        "status": "completed",
        "queue_path": resolved_input,
        "output_path": resolved_output,
        "spark_task_queue": spark_queue,
        "task_count": len(spark_queue),
    }
