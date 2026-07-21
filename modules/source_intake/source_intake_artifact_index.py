"""Build a lightweight artifact index for daily source-intake outputs.

This module is intentionally non-crawler: it only inspects files under
``storage/source_intake/<today>`` and reports presence + filesystem metadata.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from modules.source_intake.source_intake_schema import SOURCE_INTAKE_STORAGE_ROOT

ARTIFACTS = [
    "daily_collection_plan.json",
    "daily_shallow_collection.json",
    "collection_gap_report.json",
    "collector_implementation_queue.json",
    "lane_collection_summary.json",
    "source_intake_status_bundle.json",
    "source_intake_brief.md",
]


def _coerce_today(today: Optional[Any]) -> str:
    if not today:
        return date.today().isoformat()
    if isinstance(today, str):
        return today
    if isinstance(today, (datetime, date)):
        return today.isoformat()
    return str(today)


def _coerce_timestamp(seconds: Any) -> Optional[str]:
    try:
        return datetime.fromtimestamp(float(seconds)).isoformat()
    except Exception:
        return None


def _read_artifact_entry(path: str) -> Dict[str, Any]:
    try:
        stat_result = os.stat(path)
    except FileNotFoundError:
        return {"path": path, "present": False, "size_bytes": None, "last_modified": None}
    except Exception:
        return {"path": path, "present": False, "size_bytes": None, "last_modified": None}

    return {
        "path": path,
        "present": True,
        "size_bytes": int(stat_result.st_size),
        "last_modified": _coerce_timestamp(stat_result.st_mtime),
    }


def build_source_intake_artifact_index(
    today: Optional[Any] = None,
    root: Optional[str] = None,
) -> Dict[str, Any]:
    """Return an index of expected daily artifacts and filesystem status.

    Args:
        today: Optional date string/obj. Defaults to today.
        root: Optional source-intake root directory.
            Defaults to ``storage/source_intake``.
    """
    today_str = _coerce_today(today)
    base_root = root or SOURCE_INTAKE_STORAGE_ROOT
    day_root = os.path.join(base_root, today_str)

    artifacts = {}
    for artifact_name in ARTIFACTS:
        artifacts[artifact_name] = _read_artifact_entry(
            os.path.join(day_root, artifact_name)
        )

    present = [name for name, entry in artifacts.items() if entry["present"]]
    missing = [name for name, entry in artifacts.items() if not entry["present"]]

    return {
        "today": today_str,
        "day_root": day_root,
        "artifacts": artifacts,
        "summary": {
            "artifact_count": len(ARTIFACTS),
            "present_count": len(present),
            "missing_count": len(missing),
            "present_artifacts": present,
            "missing_artifacts": missing,
        },
    }


def run_source_intake_artifact_index(
    today: Optional[Any] = None,
    root: Optional[str] = None,
) -> Dict[str, Any]:
    """Build and persist a daily artifact index under ``source_intake_artifact_index.json``."""
    today_str = _coerce_today(today)
    base_root = root or SOURCE_INTAKE_STORAGE_ROOT
    day_root = os.path.join(base_root, today_str)
    index_path = os.path.join(day_root, "source_intake_artifact_index.json")

    artifact_index = build_source_intake_artifact_index(today=today_str, root=base_root)
    result = {
        "status": "write_failed",
        "today": today_str,
        "artifact_index_path": index_path,
        "artifact_index": artifact_index,
    }

    try:
        os.makedirs(day_root, exist_ok=True)
        with open(index_path, "w", encoding="utf-8") as handle:
            json.dump(artifact_index, handle, ensure_ascii=False, indent=2)
        result["status"] = "written"
    except Exception as error:
        result["error"] = str(error)

    return result
