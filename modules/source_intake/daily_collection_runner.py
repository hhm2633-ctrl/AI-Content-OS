"""Persistence wrapper for daily source collection plan generation.

This module intentionally contains no crawling or API calls.
It only builds a plan from :func:`build_daily_collection_plan` and writes
the result to disk.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from modules.source_intake.daily_collection_plan import build_daily_collection_plan
from modules.source_intake.source_intake_schema import SOURCE_INTAKE_STORAGE_ROOT

DEFAULT_OUTPUT_ROOT = SOURCE_INTAKE_STORAGE_ROOT


def _coerce_today(today: Optional[Any]) -> str:
    if not today:
        return date.today().isoformat()
    if isinstance(today, str):
        return today
    if isinstance(today, (datetime, date)):
        return today.isoformat()
    return str(today)


def run_daily_collection_plan(
    account_profiles: Optional[List[str]] = None,
    today: Optional[Any] = None,
    output_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Build and persist a daily source collection plan.

    Args:
        account_profiles: Optional lane list for planning.
        today: Optional date for plan generation.
        output_root: Root directory for persistence.
            Defaults to ``storage/source_intake``.

    Returns:
        dict: status, plan_path, plan
    """
    today_str = _coerce_today(today)
    base_root = output_root or DEFAULT_OUTPUT_ROOT
    target_dir = os.path.join(base_root, today_str)
    plan_path = os.path.join(target_dir, "daily_collection_plan.json")

    result = {
        "status": "write_failed",
        "plan_path": plan_path,
        "plan": None,
    }

    plan = build_daily_collection_plan(
        account_profiles=account_profiles,
        today=today_str,
    )
    result["plan"] = plan

    try:
        os.makedirs(target_dir, exist_ok=True)
        with open(plan_path, "w", encoding="utf-8") as handle:
            json.dump(plan, handle, ensure_ascii=False, indent=2)
        result["status"] = "written"
    except Exception as error:
        result["status"] = "write_failed"
        result["error"] = str(error)

    return result
