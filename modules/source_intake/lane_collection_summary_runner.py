"""Persistence wrapper for lane collection summary generation.

This module contains no crawling or API access. It builds a summary artifact
from an existing collection gap report.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Dict, Optional

from modules.source_intake.lane_collection_summary import build_lane_collection_summary
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


def run_lane_collection_summary(
    gap_report_path: Optional[str] = None,
    today: Optional[Any] = None,
    output_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Build and persist a lane collection summary.

    Args:
        gap_report_path: Optional explicit input path. Defaults to
            ``<output_root>/<today>/collection_gap_report.json``.
        today: Optional date used for default paths.
        output_root: Optional root directory. Defaults to
            ``storage/source_intake``.
    """
    today_str = _coerce_today(today)
    base_root = output_root or SOURCE_INTAKE_STORAGE_ROOT
    target_dir = os.path.join(base_root, today_str)
    default_input = os.path.join(target_dir, "collection_gap_report.json")

    input_path = gap_report_path or default_input
    output_path = os.path.join(target_dir, "lane_collection_summary.json")

    if not os.path.exists(input_path):
        return {
            "status": "input_missing",
            "today": today_str,
            "gap_report_path": input_path,
            "lane_collection_summary_path": output_path,
        }

    summary = build_lane_collection_summary(input_path)
    try:
        _write_json(output_path, summary)
        return {
            "status": "written",
            "today": today_str,
            "gap_report_path": input_path,
            "lane_collection_summary_path": output_path,
            "lane_collection_summary": summary,
        }
    except Exception as error:
        return {
            "status": "write_failed",
            "today": today_str,
            "gap_report_path": input_path,
            "lane_collection_summary_path": output_path,
            "lane_collection_summary": summary,
            "error": str(error),
        }
