"""Bounded account-specific deep discovery over final selected CardNews requests.

This runner never performs network work itself. All discovery is delegated to an
injected provider; provider failures degrade to additive diagnostic results and
no evidence, comments, or footage is ever fabricated.
"""

from __future__ import annotations

import copy
import re
from collections import OrderedDict
from typing import Any, Dict, List, Mapping

SCHEMA_VERSION = "account_deep_discovery_result_v1"
MAX_REQUESTS_PER_ACCOUNT = 4
SUPPORTED_ACCOUNTS = ("A", "B", "C")

# Account-specific discovery operations and artifact roles. A: news evidence;
# B: original capture / real comments / reconstruction facts; C: official
# fashion-beauty assets only.
ACCOUNT_DISCOVERY_PLANS: Dict[str, tuple] = {
    "A": (
        {"operation": "fetch_article_body", "artifact_role": "article_body"},
        {"operation": "collect_news_images", "artifact_role": "news_image"},
        {
            "operation": "locate_embedded_or_broadcast_video",
            "artifact_role": "broadcast_video",
        },
    ),
    "B": (
        {"operation": "capture_original_post", "artifact_role": "original_capture"},
        {"operation": "collect_real_comments", "artifact_role": "real_comment"},
        {
            "operation": "extract_reconstruction_scene_facts",
            "artifact_role": "reconstruction_scene_fact",
        },
    ),
    "C": (
        {
            "operation": "collect_official_show_or_lookbook",
            "artifact_role": "official_show_lookbook",
        },
        {"operation": "collect_campaign_assets", "artifact_role": "campaign_asset"},
        {"operation": "collect_official_product_assets", "artifact_role": "official_product"},
        {"operation": "collect_official_video", "artifact_role": "official_video"},
    ),
}

_AP_PATTERN = re.compile(r"(^|\W)ap(\W|$)|associated\s+press", re.IGNORECASE)
_AP_FIELDS = ("license", "source", "provider", "agency", "credit")


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _closed(reason_code: str, reason: str) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "closed",
        "reason_code": reason_code,
        "reason": reason,
        "execution_enabled": False,
        "network_executed": False,
        "accounts": {},
        "failures": [],
    }


def _is_ap_asset(asset: Mapping[str, Any]) -> bool:
    return any(_AP_PATTERN.search(_text(asset.get(field))) for field in _AP_FIELDS)


def _sanitize_assets(role: str, raw_assets: Any) -> Dict[str, List[Dict[str, Any]]]:
    """Keep only provider-supplied assets; never synthesize evidence."""

    assets: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for raw in raw_assets if isinstance(raw_assets, list) else []:
        if not isinstance(raw, Mapping):
            rejected.append({"reason": "malformed_asset"})
            continue
        asset = copy.deepcopy(dict(raw))
        asset["artifact_role"] = role
        if role == "real_comment" and raw.get("is_real_comment") is not True:
            rejected.append(
                {
                    "reason": "unverified_comment_rejected",
                    "detail": "real comments require provider is_real_comment=true",
                    "asset": asset,
                }
            )
            continue
        if _is_ap_asset(raw):
            asset["reference_only"] = True
            asset["usable_in_production"] = False
            asset["restriction_reason"] = "ap_reference_only"
        else:
            asset.setdefault("reference_only", False)
            asset.setdefault("usable_in_production", True)
        assets.append(asset)
    return {"assets": assets, "rejected": rejected}


def _normalize_selection(selection: Any) -> "OrderedDict[str, List[Dict[str, Any]]]":
    """Accept cardnews_final_selection_v1, owner queue payloads, or plain lists."""

    per_account: "OrderedDict[str, List[Dict[str, Any]]]" = OrderedDict(
        (account, []) for account in SUPPORTED_ACCOUNTS
    )

    entries: List[Any] = []
    if isinstance(selection, Mapping):
        accounts = selection.get("accounts")
        if isinstance(accounts, Mapping):
            for account in SUPPORTED_ACCOUNTS:
                bucket = accounts.get(account)
                selected = bucket.get("selected") if isinstance(bucket, Mapping) else None
                for item in selected if isinstance(selected, list) else []:
                    if isinstance(item, Mapping):
                        entries.append({**dict(item), "account": account})
        elif isinstance(selection.get("requests"), list):
            entries.extend(item for item in selection["requests"] if isinstance(item, Mapping))
    elif isinstance(selection, list):
        entries.extend(item for item in selection if isinstance(item, Mapping))

    for entry in entries:
        account = _text(entry.get("account")).upper()
        candidate_id = _text(entry.get("candidate_id"))
        if account in per_account and candidate_id:
            per_account[account].append(
                {
                    "candidate_id": candidate_id,
                    "title": _text(entry.get("title")),
                    "category": _text(entry.get("category")) or _text(entry.get("category_id")),
                    "grade": _text(entry.get("grade")),
                    "source_urls": [
                        _text(url)
                        for url in (entry.get("source_urls") or [])
                        if isinstance(url, str) and url.strip()
                    ],
                }
            )
    return per_account


def _dedupe_requests(
    account: str,
    requests: List[Dict[str, Any]],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Keep the first request for each account/candidate/category discovery unit."""

    unique: List[Dict[str, Any]] = []
    duplicates: List[Dict[str, Any]] = []
    seen = set()
    operation_count = len(ACCOUNT_DISCOVERY_PLANS[account])

    for request in requests:
        key = (account, request["candidate_id"], request["category"])
        if key in seen:
            duplicates.append(
                {
                    "candidate_id": request["candidate_id"],
                    "category": request["category"],
                    "duplicate_operations_eliminated": operation_count,
                }
            )
            continue
        seen.add(key)
        unique.append(request)

    return unique, duplicates


def run_account_deep_discovery(
    selection: Any,
    provider: Any,
    max_per_account: int = MAX_REQUESTS_PER_ACCOUNT,
) -> Dict[str, Any]:
    """Execute account-specific discovery for selected requests only, bounded."""

    if provider is None or not callable(getattr(provider, "discover", None)):
        return _closed(
            "missing_provider",
            "an injected provider with a callable discover(account, operation, request) is required",
        )

    per_account = _normalize_selection(selection)
    if not any(per_account.values()):
        return _closed("no_selected_requests", "no final selected CardNews requests to discover")

    bound = max(0, int(max_per_account))
    network_executed = False
    failures: List[Dict[str, Any]] = []
    accounts: Dict[str, Any] = {}

    for account in SUPPORTED_ACCOUNTS:
        requested = per_account[account]
        unique_requests, duplicates = _dedupe_requests(account, requested)
        executed = unique_requests[:bound]
        skipped = [entry["candidate_id"] for entry in unique_requests[bound:]]
        results: List[Dict[str, Any]] = []

        for request in executed:
            operations: List[Dict[str, Any]] = []
            for step in ACCOUNT_DISCOVERY_PLANS[account]:
                record: Dict[str, Any] = {
                    "operation": step["operation"],
                    "artifact_role": step["artifact_role"],
                    "network_used": False,
                    "assets": [],
                    "rejected": [],
                }
                try:
                    raw = provider.discover(account, step["operation"], dict(request))
                except Exception as error:  # provider failures stay additive
                    record["status"] = "provider_failed"
                    record["error"] = str(error) or type(error).__name__
                    failures.append(
                        {
                            "account": account,
                            "candidate_id": request["candidate_id"],
                            "operation": step["operation"],
                            "error": record["error"],
                        }
                    )
                    operations.append(record)
                    continue

                if not isinstance(raw, Mapping) or _text(raw.get("status")) == "error":
                    record["status"] = "provider_failed"
                    record["error"] = (
                        _text(raw.get("error")) if isinstance(raw, Mapping) else ""
                    ) or "provider returned an invalid result"
                    failures.append(
                        {
                            "account": account,
                            "candidate_id": request["candidate_id"],
                            "operation": step["operation"],
                            "error": record["error"],
                        }
                    )
                    operations.append(record)
                    continue

                record["network_used"] = bool(raw.get("network_used", False))
                network_executed = network_executed or record["network_used"]
                sanitized = _sanitize_assets(step["artifact_role"], raw.get("assets"))
                record["assets"] = sanitized["assets"]
                record["rejected"] = sanitized["rejected"]
                record["status"] = "ok" if sanitized["assets"] else "empty"
                operations.append(record)

            results.append(
                {
                    "candidate_id": request["candidate_id"],
                    "title": request["title"],
                    "category": request["category"],
                    "operations": operations,
                }
            )

        accounts[account] = {
            "requested": len(requested),
            "unique_requested": len(unique_requests),
            "executed": len(executed),
            "skipped_over_limit": skipped,
            "deduplicated_requests": duplicates,
            "duplicate_operations_eliminated": sum(
                duplicate["duplicate_operations_eliminated"]
                for duplicate in duplicates
            ),
            "provider_calls_without_dedupe": min(len(requested), bound)
            * len(ACCOUNT_DISCOVERY_PLANS[account]),
            "provider_calls_planned": len(executed)
            * len(ACCOUNT_DISCOVERY_PLANS[account]),
            "provider_call_reduction": (
                min(len(requested), bound) - len(executed)
            )
            * len(ACCOUNT_DISCOVERY_PLANS[account]),
            "results": results,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "completed",
        "reason_code": "selected_only_bounded_execution",
        "execution_enabled": True,
        "network_executed": network_executed,
        "provider": _text(getattr(provider, "name", "")) or type(provider).__name__,
        "max_per_account": bound,
        "accounts": accounts,
        "failures": failures,
    }


__all__ = [
    "run_account_deep_discovery",
    "ACCOUNT_DISCOVERY_PLANS",
    "MAX_REQUESTS_PER_ACCOUNT",
    "SCHEMA_VERSION",
    "SUPPORTED_ACCOUNTS",
]
