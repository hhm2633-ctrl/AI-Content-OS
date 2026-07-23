"""Bridge sanitized account deep-discovery outputs into traceable render inputs.

This adapter is intentionally pure: it never fetches data and never writes
outside the process. It only reshapes already-local deep-discovery payloads into
compact, deterministic media/source candidates for downstream render planning.
"""

from __future__ import annotations

import copy
import hashlib
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from modules.media_intelligence.source_editorial_localizer import (
    localize_discovered_media_assets,
)
from modules.source_intake.workflow_media_discovery_bridge import (
    run_workflow_media_discovery,
)


SCHEMA_VERSION = "discovery_result_render_bridge_v1"
RENDER_BLOCK_STATUSES = frozenset({"rejected", "blocked", "invalid"})
_AP_FIELDS = ("credit", "source", "provider", "agency", "publisher")
_SAFE_PATH = re.compile(r"[^0-9A-Za-z._-]+")


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _objects(value: Any) -> List[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, Mapping)]


def _first(value: Any, *keys: str) -> Any:
    if not isinstance(value, Mapping):
        return None
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, str):
            text = candidate.strip()
            if text:
                return text
        elif candidate is not None:
            return candidate
    return None


def _append_diagnostic(
    sink: List[Dict[str, Any]],
    reason_code: str,
    reason: str,
    **context: Any,
) -> None:
    row = {"reason_code": reason_code, "reason": reason}
    row.update(context)
    sink.append(row)


def _is_true(value: Any) -> bool:
    return value is True


def _is_ap_reference(asset: Mapping[str, Any]) -> bool:
    if asset.get("ap_source") is True:
        return True
    if _is_true(asset.get("ap_source")):
        return True
    for field in _AP_FIELDS:
        raw = _text(asset.get(field)).lower()
        if raw == "ap" or raw == "associated press":
            return True
    return False


def _is_generated(asset: Mapping[str, Any]) -> bool:
    if _is_true(asset.get("generated")) or _is_true(asset.get("is_generated")):
        return True
    origin = _text(asset.get("origin")).lower()
    asset_class = _text(asset.get("asset_class")).lower()
    generation_marker = asset.get("generation_source")
    if _text(generation_marker).lower() == "generated":
        return True
    return origin == "generated" or "generated" in origin or asset_class == "generated"


def _build_media_record(
    account: str | None,
    candidate_id: str | None,
    candidate_title: str | None,
    operation: str,
    artifact_role: str,
    asset: Mapping[str, Any],
    operation_index: int,
    asset_index: int,
    diagnostics: List[Dict[str, Any]],
) -> Dict[str, Any]:
    source_url = _first(
        asset,
        "source_url",
        "url",
        "source_page",
        "source_page_url",
        "link",
        "canonical_url",
    )
    media_url = _first(
        asset,
        "local_path",
        "thumbnail_url",
        "remote_url",
        "media_url",
        "url",
        "locator",
        "path",
    )
    if media_url is None and artifact_role == "real_comment":
        media_url = source_url
    media_type = _first(asset, "media_type", "type", "kind")
    if media_type is not None:
        media_type = str(media_type).strip().lower() or "unknown"
    publisher = _first(asset, "publisher", "source", "provider", "agency")
    channel = _first(asset, "channel", "source_channel", "distribution_channel")
    published_at = _first(
        asset,
        "published_at",
        "published_time",
        "published_ts",
        "captured_at",
        "published",
    )
    rights_status = _first(asset, "rights_status", "rights", "license")

    status = _text(asset.get("status")).lower()
    reference_only = bool(asset.get("reference_only")) or _is_ap_reference(asset)
    generated = _is_generated(asset)

    render_restrictions: List[str] = []
    if status in RENDER_BLOCK_STATUSES:
        render_restrictions.append(f"asset_status_{status or 'invalid'}")
    if reference_only:
        render_restrictions.append("reference_only")
        if _is_ap_reference(asset):
            render_restrictions.append("ap_reference_only")
    if generated:
        render_restrictions.append("generated_synthetic")
    if asset.get("render_allowed") is False:
        render_restrictions.append("provider_render_denied")
    if asset.get("usable_in_production") is False:
        render_restrictions.append("production_use_denied")
    if asset.get("metadata_only") is True or artifact_role in {
        "article_body",
        "related_news",
    }:
        render_restrictions.append("metadata_only")
    if source_url is None:
        render_restrictions.append("source_url_missing")
        _append_diagnostic(
            diagnostics,
            "missing_source_url",
            "media/source row has no usable source URL",
            account=account,
            candidate_id=candidate_id,
            operation=operation,
            artifact_role=artifact_role,
            operation_index=operation_index,
            asset_index=asset_index,
        )
    if media_url is None:
        render_restrictions.append("media_url_missing")
        _append_diagnostic(
            diagnostics,
            "missing_media_url",
            "media/source row has no media locator",
            account=account,
            candidate_id=candidate_id,
            operation=operation,
            artifact_role=artifact_role,
            operation_index=operation_index,
            asset_index=asset_index,
        )

    is_real_comment = _is_true(asset.get("is_real_comment"))
    real_comment_provenance: Dict[str, Any] | None = None
    if artifact_role == "real_comment":
        real_comment_provenance = {
            "is_real_comment": bool(asset.get("is_real_comment")),
            "comment_id": _first(asset, "comment_id"),
            "identity_masked": bool(asset.get("identity_masked")),
        }
        if _first(asset, "text") is not None:
            real_comment_provenance["text"] = str(_first(asset, "text"))
        if not is_real_comment:
            render_restrictions.append("real_comment_provenance_missing")
            _append_diagnostic(
                diagnostics,
                "invalid_real_comment_provenance",
                "real_comment artifact requires is_real_comment=true",
                account=account,
                candidate_id=candidate_id,
                operation=operation,
                artifact_role=artifact_role,
                operation_index=operation_index,
                asset_index=asset_index,
            )

    render_allowed = not render_restrictions
    return {
        "account": account,
        "candidate_id": candidate_id,
        "candidate_title": candidate_title,
        "operation": operation,
        "operation_artifact_role": artifact_role,
        "source_url": source_url,
        "media_url": media_url,
        "media_type": media_type,
        "publisher": publisher,
        "channel": channel,
        "published_at": published_at,
        "rights_status": rights_status,
        "reference_only": bool(reference_only),
        "ap_reference_only": bool(_is_ap_reference(asset)),
        "generated": bool(generated),
        "status": status or None,
        "render_allowed": render_allowed,
        "render_restrictions": sorted(set(render_restrictions)),
        "raw_source_asset": copy.deepcopy(dict(asset)),
        "real_comment_provenance": real_comment_provenance,
    }


def _candidate_rows(
    account: str | None,
    candidate: Mapping[str, Any],
    diagnostics: List[Dict[str, Any]],
) -> Dict[str, Any]:
    candidate_id = _text(candidate.get("candidate_id")) or _text(candidate.get("id")) or None
    candidate_title = _text(candidate.get("title")) or None
    result: Dict[str, Any] = {
        "account": account,
        "candidate_id": candidate_id,
        "candidate_title": candidate_title,
        "media_source_inputs": [],
        "diagnostics": [],
        "render_allowed_count": 0,
    }

    if not candidate_id:
        _append_diagnostic(
            diagnostics,
            "missing_candidate_id",
            "candidate record has no candidate_id",
            account=account,
            candidate_title=candidate_title,
        )
        result["diagnostics"].append(
            {
                "reason_code": "missing_candidate_id",
                "reason": "candidate record has no candidate_id",
            }
        )

    operations = _objects(candidate.get("operations"))
    if not operations:
        _append_diagnostic(
            diagnostics,
            "candidate_operations_missing",
            "candidate has no operations",
            account=account,
            candidate_id=candidate_id,
        )
        result["diagnostics"].append(
            {
                "reason_code": "candidate_operations_missing",
                "reason": "candidate has no operations",
            }
        )
        return result

    for operation_index, operation in enumerate(operations, start=1):
        operation_name = _text(operation.get("operation"))
        artifact_role = _text(operation.get("artifact_role")) or operation_name
        if not operation_name:
            _append_diagnostic(
                diagnostics,
                "missing_operation_name",
                "operation row has no operation string",
                account=account,
                candidate_id=candidate_id,
                operation_index=operation_index,
            )
            result["diagnostics"].append(
                {
                    "reason_code": "missing_operation_name",
                    "reason": "operation row has no operation string",
                    "operation_index": operation_index,
                }
            )
            continue

        assets = _objects(operation.get("assets"))
        for asset_index, asset in enumerate(assets, start=1):
            source_input = _build_media_record(
                account=account,
                candidate_id=candidate_id,
                candidate_title=candidate_title,
                operation=operation_name,
                artifact_role=artifact_role,
                asset=asset,
                operation_index=operation_index,
                asset_index=asset_index,
                diagnostics=diagnostics,
            )
            result["media_source_inputs"].append(source_input)
            if source_input["render_allowed"]:
                result["render_allowed_count"] += 1
        if not assets:
            _append_diagnostic(
                diagnostics,
                "operation_assets_missing",
                "operation returned no assets",
                account=account,
                candidate_id=candidate_id,
                operation=operation_name,
                operation_index=operation_index,
            )
            result["diagnostics"].append(
                {
                    "reason_code": "operation_assets_missing",
                    "reason": "operation returned no assets",
                    "operation": operation_name,
                    "operation_index": operation_index,
                }
            )

    return result


def run_discovery_result_render_bridge(discovery_result: Any) -> Dict[str, Any]:
    """Convert sanitized deep-discovery results into renderable media/source records.

    No input is mutated and no network writes are performed.
    """

    if not isinstance(discovery_result, Mapping):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "closed",
            "reason_code": "invalid_discovery_result",
            "reason": "discovery_result must be a mapping",
            "candidates": [],
            "candidate_count": 0,
            "diagnostics": [],
            "totals": {
                "media_input_count": 0,
                "render_allowed_count": 0,
                "operation_count": 0,
            },
        }

    source_payload = copy.deepcopy(dict(discovery_result))
    diagnostics: List[Dict[str, Any]] = []
    candidate_records: List[Dict[str, Any]] = []

    accounts = source_payload.get("accounts")
    if isinstance(accounts, Mapping):
        for account, raw_account in accounts.items():
            if not isinstance(raw_account, Mapping):
                _append_diagnostic(
                    diagnostics,
                    "malformed_account_record",
                    "accounts entry is not an object",
                    account=str(account),
                )
                continue
            candidate_records.extend(
                (
                    _candidate_rows(
                        _text(account),
                        candidate,
                        diagnostics,
                    )
                    for candidate in _objects(raw_account.get("results"))
                )
            )
    elif _objects(discovery_result.get("results")):
        candidate_records = [
            _candidate_rows(_text(discovery_result.get("account")), candidate, diagnostics)
            for candidate in _objects(discovery_result.get("results"))
        ]
    elif _objects(discovery_result.get("candidates")):
        candidate_records = [
            _candidate_rows(_text(candidate.get("account")), candidate, diagnostics)
            for candidate in _objects(discovery_result.get("candidates"))
        ]
    else:
        _append_diagnostic(
            diagnostics,
            "no_candidate_records_found",
            "no readable accounts/results/candidates entries were found",
        )

    media_input_count = sum(len(item["media_source_inputs"]) for item in candidate_records)
    render_allowed_count = sum(item["render_allowed_count"] for item in candidate_records)
    operation_count = 0
    for candidate in _objects(discovery_result.get("results")):
        operation_count += len(_objects(candidate.get("operations")))
    if not candidate_records:
        status = "closed"
        reason_code = "no_candidates"
        reason = "no candidate records were extracted"
    else:
        status = "degraded" if diagnostics else "ready"
        reason_code = "converted_with_diagnostics" if diagnostics else "conversion_completed"
        reason = (
            "discovery records were converted with additive diagnostics"
            if diagnostics
            else "discovery records were converted"
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "reason_code": reason_code,
        "reason": reason,
        "candidates": copy.deepcopy(candidate_records),
        "candidate_count": len(candidate_records),
        "diagnostics": copy.deepcopy(diagnostics),
        "totals": {
            "media_input_count": media_input_count,
            "render_allowed_count": render_allowed_count,
            "operation_count": operation_count,
        },
        "source_record_preserved": source_payload,
    }


def build_discovery_result_render_inputs(discovery_result: Any) -> Dict[str, Any]:
    """Compatibility name retained for future wiring."""

    return run_discovery_result_render_bridge(discovery_result)


def run_discovery_result_render_bridge_with_supplements(
    discovery_result: Any,
) -> Dict[str, Any]:
    """Add shortage-triggered media discovery before the pure render bridge."""

    if not isinstance(discovery_result, Mapping):
        return run_discovery_result_render_bridge(discovery_result)
    enriched = copy.deepcopy(dict(discovery_result))
    supplemental_diagnostics: List[Dict[str, Any]] = []

    def enrich_candidate(account: str, candidate: Dict[str, Any]) -> None:
        operations = candidate.get("operations")
        operations = operations if isinstance(operations, list) else []
        visual_count = 0
        for operation in operations:
            if not isinstance(operation, Mapping):
                continue
            for asset in _objects(operation.get("assets")):
                if _first(asset, "local_path", "thumbnail_url", "remote_url", "media_url"):
                    visual_count += 1
        if visual_count >= 2:
            return
        request = {
            "title": _text(candidate.get("title")),
            "category": _text(candidate.get("category")),
            "emotion": _text(candidate.get("emotion")),
            "reaction_query": _text(candidate.get("reaction_query")),
        }
        discovery = run_workflow_media_discovery(request, account=account)
        render_assets = discovery.get("render_assets")
        local_assets = [
            asset
            for asset in render_assets
            if isinstance(asset, Mapping)
            and bool(_text(asset.get("local_path")))
            and asset.get("render_allowed") is True
        ] if isinstance(render_assets, list) else []
        remote_assets = [
            asset
            for asset in render_assets
            if isinstance(asset, Mapping)
            and not _text(asset.get("local_path"))
            and bool(_text(asset.get("remote_url")))
            and asset.get("render_allowed") is True
        ] if isinstance(render_assets, list) else []
        candidate_key = _text(candidate.get("candidate_id") or candidate.get("id"))
        safe_key = _SAFE_PATH.sub("-", candidate_key).strip("-")
        if not safe_key:
            safe_key = hashlib.sha256(
                _text(candidate.get("title")).encode("utf-8")
            ).hexdigest()[:16]
        localization = localize_discovered_media_assets(
            remote_assets,
            Path(
                os.getenv(
                    "AI_CONTENT_OS_OPEN_MEDIA_DIR",
                    r"F:\AI-Content-OS-Data\open_media",
                )
            )
            / safe_key,
            query=_text(candidate.get("title") or candidate.get("category")),
            max_assets=max(1, 2 - visual_count),
        )
        localized_assets = localization.get("assets")
        localized_assets = localized_assets if isinstance(localized_assets, list) else []
        render_assets = [*local_assets, *localized_assets]
        if render_assets:
            operations.append(
                {
                    "operation": "search_supplemental_media",
                    "artifact_role": "supplemental_visual",
                    "assets": copy.deepcopy(render_assets),
                }
            )
            candidate["operations"] = operations
        supplemental_diagnostics.append(
            {
                "account": account,
                "candidate_id": _text(candidate.get("candidate_id") or candidate.get("id")),
                "status": discovery.get("status"),
                "reason_code": discovery.get("reason_code"),
                "asset_count": discovery.get("asset_count", 0),
                "render_asset_count": discovery.get("render_asset_count", 0),
                "localized_render_asset_count": len(localized_assets),
                "local_reaction_asset_count": len(local_assets),
                "localization": copy.deepcopy(localization),
                "provider_diagnostics": copy.deepcopy(discovery.get("diagnostics", [])),
            }
        )

    accounts = enriched.get("accounts")
    if isinstance(accounts, Mapping):
        for account, raw_account in accounts.items():
            if not isinstance(raw_account, dict):
                continue
            for candidate in _objects(raw_account.get("results")):
                if isinstance(candidate, dict):
                    enrich_candidate(_text(account), candidate)
    else:
        for candidate in _objects(enriched.get("results")):
            if isinstance(candidate, dict):
                enrich_candidate(_text(enriched.get("account")), candidate)

    result = run_discovery_result_render_bridge(enriched)
    result["supplemental_media"] = {
        "status": "completed",
        "shortage_threshold": 2,
        "all_accounts_eligible": True,
        "diagnostics": supplemental_diagnostics,
    }
    return result


__all__ = [
    "SCHEMA_VERSION",
    "run_discovery_result_render_bridge",
    "run_discovery_result_render_bridge_with_supplements",
    "build_discovery_result_render_inputs",
]
