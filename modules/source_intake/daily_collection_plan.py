"""Deterministic daily source collection planning for shallow-first intake.

This module is the planning contract only (no crawling, no LLM/token calls).
It decides:
- which source IDs are scanned shallowly for each requested lane
- which sources are blocked/skip-eligible and why
- default deep-dive trigger guardrails for later phases
- storage policy for index output and external artifacts
"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from modules.source_intake.source_capability_map import SourceCapabilityMap
from modules.source_intake.source_intake_metrics import DEFAULT_DEEP_DIVE_THRESHOLD
from modules.source_intake.source_intake_schema import (
    SOURCE_INTAKE_STORAGE_ROOT,
    shallow_index_dir,
    source_data_root,
)

SCHEMA_VERSION = "daily_source_collection_plan_v1"

DEFAULT_LANES: Dict[str, List[str]] = {
    "news_society_economy": [
        "naver_news",
        "daum_news",
        "nate_news_rank",
        "hankyung_economy",
        "mk_economy",
        "moneytoday",
        "edaily",
        "yonhap",
        "newsis",
        "news1",
    ],
    "entertainment_news": [
        "nate_news_rank",
        "naver_news",
        "daum_news",
        "theqoo",
        "dcinside",
        "ppomppu",
    ],
    "dopamine_community": [
        "nate_pann",
        "fmkorea",
        "bobaedream",
        "dcinside",
        "theqoo",
        "dogdrip",
        "ruliweb",
    ],
    "beauty_fashion": [
        "fashionn",
        "fashionbiz",
        "apparelnews",
        "allure_beauty",
        "vogue_beauty",
        "wkorea_beauty",
        "gq_grooming",
        "musinsa_monthly_ranking",
        "glowpick_ranking",
        "musinsa_beauty",
        "oliveyoung_ranking",
        "musinsa_boutique",
    ],
    "lifestyle_knowledge": [
        "naver_news",
        "daum_news",
        "newsis",
        "news1",
        "nate_pann",
    ],
}


def _coerce_today(today: Optional[Any]) -> str:
    if not today:
        return date.today().isoformat()
    if isinstance(today, str):
        return today
    if isinstance(today, (datetime, date)):
        return today.isoformat()
    return str(today)


def _normalise_requested_lanes(account_profiles: Optional[Any]) -> List[str]:
    if not account_profiles:
        return list(DEFAULT_LANES.keys())
    seen = set()
    ordered: List[str] = []
    for lane_id in account_profiles:
        if lane_id in seen:
            continue
        seen.add(lane_id)
        ordered.append(lane_id)
    return ordered


def _coerce_capability_map(source_capabilities: Optional[Any]) -> SourceCapabilityMap:
    if source_capabilities is None or isinstance(source_capabilities, SourceCapabilityMap):
        return source_capabilities or SourceCapabilityMap()

    class _DictBackedCapabilityMap:
        def __init__(self, raw: Any) -> None:
            self._entries: Dict[str, Dict[str, Any]] = {}
            if isinstance(raw, dict):
                if raw.get("sources") and isinstance(raw["sources"], list):
                    for entry in raw["sources"]:
                        if isinstance(entry, dict) and entry.get("source_id"):
                            self._entries[entry["source_id"]] = entry
                else:
                    for key, entry in raw.items():
                        if isinstance(entry, dict):
                            source_id = entry.get("source_id") or key
                            self._entries[source_id] = dict(entry, source_id=source_id)
            elif isinstance(raw, list):
                for entry in raw:
                    if isinstance(entry, dict) and entry.get("source_id"):
                        self._entries[entry["source_id"]] = entry

        def get(self, source_id: str) -> Dict[str, Any]:
            return self._entries.get(
                source_id,
                {
                    "source_id": source_id,
                    "url": "",
                    "source_type": "unknown",
                    "access_status": "blocked",
                    "collector_allowed": False,
                    "blocked_reason": "unknown_source",
                    "expected_metrics": [],
                    "channel_candidates": [],
                },
            )

        def is_collector_allowed(self, source_id: str) -> bool:
            entry = self.get(source_id)
            return bool(entry.get("collector_allowed")) and entry.get("access_status") == "ok"

        def skip_report(self, source_id: str) -> Dict[str, Any]:
            entry = self.get(source_id)
            return {
                "source_id": source_id,
                "attempted": False,
                "success": False,
                "skipped": True,
                "skip_reason": entry.get("blocked_reason", "access_blocked"),
                "access_status": entry.get("access_status", "blocked"),
                "workflow_impact": "none",
            }

    return _DictBackedCapabilityMap(source_capabilities)


def _filter_sources(
    lane_id: str,
    source_ids: List[str],
    capability_map: SourceCapabilityMap,
) -> Dict[str, Any]:
    allowed: List[str] = []
    excluded: List[Dict[str, Any]] = []
    seen = set()
    excluded_seen = set()

    for source_id in source_ids:
        if capability_map.is_collector_allowed(source_id):
            if source_id not in seen:
                seen.add(source_id)
                allowed.append(source_id)
        elif source_id not in excluded_seen:
            excluded_seen.add(source_id)
            report = capability_map.skip_report(source_id)
            report["lane_id"] = lane_id
            excluded.append(report)

    return {"shallow_profiles": allowed, "excluded_sources": excluded}


def _build_storage_policy(today: str) -> Dict[str, Any]:
    source_root = source_data_root()
    shallow_index_path = shallow_index_dir(today).replace("\\", "/")

    return {
        "shallow_only_index": {
            "small_index_root": SOURCE_INTAKE_STORAGE_ROOT,
            "small_index_path": shallow_index_path,
            "storage_drive": "C",
        },
        "deep_dive_raw_artifacts": {
            "raw_artifacts_root": source_root,
            "artifacts_drive": os.path.splitdrive(source_root)[0] or "F:",
            "write_to_external_storage_root": True,
        },
    }


def build_daily_collection_plan(
    account_profiles: Optional[List[str]],
    source_capabilities: Optional[Any] = None,
    today: Optional[Any] = None,
) -> Dict[str, Any]:
    """Build deterministic lane-level daily collection plan.

    The planner is strict but non-fatal:
    - unknown lane ids are preserved in output with no sources
    - blocked sources are excluded and explicitly recorded
    - every output lane is shallow-only by contract
    """
    today_str = _coerce_today(today)
    requested_lanes = _normalise_requested_lanes(account_profiles)
    capability_map = _coerce_capability_map(source_capabilities)

    lanes: List[Dict[str, Any]] = []
    unknown_lanes: List[str] = []
    for lane_id in requested_lanes:
        source_ids = DEFAULT_LANES.get(lane_id)
        if source_ids is None:
            unknown_lanes.append(lane_id)
            lanes.append({
                "lane_id": lane_id,
                "shallow_profiles": [],
                "excluded_sources": [],
                "shallow_only": True,
                "deep_dive_enabled": False,
                "deep_dive_trigger_policy": {
                    "enabled": False,
                    "score_threshold": DEFAULT_DEEP_DIVE_THRESHOLD,
                    "repeat_source_min_hits": 2,
                    "repeat_source_window_days": 1,
                },
                "storage_policy": _build_storage_policy(today_str),
                "plan_status": "lane_unknown",
            })
            continue

        filtered = _filter_sources(lane_id, source_ids, capability_map)
        lanes.append({
            "lane_id": lane_id,
            "shallow_profiles": filtered["shallow_profiles"],
            "excluded_sources": filtered["excluded_sources"],
            "shallow_only": True,
            "deep_dive_enabled": False,
            "deep_dive_trigger_policy": {
                "enabled": False,
                "score_threshold": DEFAULT_DEEP_DIVE_THRESHOLD,
                "repeat_source_min_hits": 2,
                "repeat_source_window_days": 1,
            },
            "storage_policy": _build_storage_policy(today_str),
            "plan_status": "ok" if filtered["shallow_profiles"] else "no_collectable_sources",
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "date": today_str,
        "plan_status": "ok" if any(lane["plan_status"] == "ok" for lane in lanes) else "empty_plan",
        "unknown_lanes": unknown_lanes,
        "lanes": lanes,
    }
