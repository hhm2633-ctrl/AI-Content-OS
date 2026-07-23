"""Canonical manual-publishing handoff for controller-approved CardNews."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from modules.card_news.production_controller import MANUAL_UPLOAD_READY, canonical_hash


SCHEMA_VERSION = "cardnews_production_release_handoff_v1"
RENDERABLE_RIGHTS = {
    "approved", "cleared", "licensed", "owned", "owner_approved", "public_domain",
}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _blocked(reason_code: str) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "blocked",
        "reason_code": reason_code,
        "actual_publish": False,
        "publish_executed": False,
        "upload_executed": False,
    }


def _package_index(packages: Any) -> Dict[str, Mapping[str, Any]]:
    if isinstance(packages, Mapping):
        rows = packages.get("packages") if isinstance(packages.get("packages"), list) else [packages]
    elif isinstance(packages, Sequence) and not isinstance(packages, (str, bytes)):
        rows = packages
    else:
        rows = []
    result: Dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        package = row.get("package") if isinstance(row.get("package"), Mapping) else row
        candidate = package.get("candidate") if isinstance(package.get("candidate"), Mapping) else {}
        candidate_id = _text(candidate.get("candidate_id")) or _text(package.get("candidate_id"))
        if candidate_id:
            result[candidate_id] = package
    return result


def _asset_index(package: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    evidence = package.get("evidence") if isinstance(package.get("evidence"), Mapping) else {}
    rows = evidence.get("assets") if isinstance(evidence.get("assets"), list) else []
    return {
        _text(row.get("asset_id")): copy.deepcopy(dict(row))
        for row in rows
        if isinstance(row, Mapping) and _text(row.get("asset_id"))
    }


def build_production_release_handoff(
    controller_state: Any,
    render_manifest: Any,
    packages: Any,
) -> Dict[str, Any]:
    """Convert an accepted controller chain without granting a new approval."""

    if not isinstance(controller_state, Mapping):
        return _blocked("controller_state_missing")
    if (
        controller_state.get("state") != MANUAL_UPLOAD_READY
        or controller_state.get("manual_upload_ready") is not True
    ):
        return _blocked("manual_upload_not_ready")
    accounts = {_text(value) for value in controller_state.get("accounts", []) if _text(value)}
    owner_qa_ids = controller_state.get("representative_qa_receipt_ids")
    batch_qa_hashes = controller_state.get("batch_qa_receipt_hashes")
    expected_candidates = set(controller_state.get("candidate_ids", []))
    if (
        not isinstance(owner_qa_ids, Mapping)
        or set(owner_qa_ids) != accounts
        or not all(_text(value) for value in owner_qa_ids.values())
        or not isinstance(batch_qa_hashes, Mapping)
        or set(batch_qa_hashes) != expected_candidates
    ):
        return _blocked("owner_visual_approval_missing")
    if not isinstance(render_manifest, Mapping):
        return _blocked("render_manifest_missing")
    output_set_id = _text(render_manifest.get("output_set_id"))
    if not output_set_id:
        return _blocked("output_set_id_missing")

    package_by_candidate = _package_index(packages)
    records = render_manifest.get("records") if isinstance(render_manifest.get("records"), list) else []
    cards = []
    rendered_assets: Dict[str, Dict[str, Any]] = {}
    attribution_receipts = []
    rendered_candidates = set()
    title = ""
    for record in records:
        if not isinstance(record, Mapping) or record.get("status") != "render_completed_pending_visual_qa":
            continue
        candidate_id = _text(record.get("candidate_id"))
        if candidate_id not in expected_candidates:
            continue
        rendered_candidates.add(candidate_id)
        package = package_by_candidate.get(candidate_id, {})
        candidate = package.get("candidate") if isinstance(package.get("candidate"), Mapping) else {}
        title = title or _text(candidate.get("title"))
        package_assets = _asset_index(package)
        for raw_id in record.get("rendered_asset_ids", []):
            asset_id = _text(raw_id)
            if asset_id and asset_id in package_assets:
                rendered_assets[asset_id] = package_assets[asset_id]
        for receipt in record.get("attribution_receipt", []):
            if isinstance(receipt, Mapping):
                attribution_receipts.append(copy.deepcopy(dict(receipt)))
        for raw_path in record.get("outputs", []):
            path = _text(raw_path)
            if path:
                cards.append({"path": path, "index": len(cards) + 1, "exists": Path(path).is_file()})
    if rendered_candidates != expected_candidates or not cards:
        return _blocked("render_scope_incomplete")

    rendered_asset_ids = sorted(rendered_assets)
    render_allowed_asset_ids = sorted(
        asset_id
        for asset_id, asset in rendered_assets.items()
        if (
            asset.get("render_allowed") is True
            or _text(asset.get("rights_status")).lower() in RENDERABLE_RIGHTS
        )
        and _text(asset.get("rights_status")).lower() != "blocked"
    )
    rights_ready = bool(rendered_asset_ids) and rendered_asset_ids == render_allowed_asset_ids
    blockers = [] if rights_ready and all(card["exists"] for card in cards) else [
        "rendered_asset_rights_or_file_blocked"
    ]
    compliance_id = "controller-release-" + canonical_hash({
        "output_set_id": output_set_id,
        "assets": rendered_asset_ids,
    })[:20]
    attestation = {
        "schema_version": 1,
        "contract": "card_news_pre_publish_attestation_v1",
        "output_set_id": output_set_id,
        "cards": cards,
        "quality": {
            "passed": True,
            "source": "owner_visual_approval",
            "owner_visual_approval_receipt_ids": copy.deepcopy(dict(owner_qa_ids)),
            "batch_visual_qa_receipt_hashes": copy.deepcopy(dict(batch_qa_hashes)),
        },
        "rights": {"status": "pass" if rights_ready else "blocked", "ready": rights_ready},
        "evidence": {
            "status": "applied" if rendered_asset_ids else "unavailable",
            "available": bool(rendered_asset_ids),
            "applied": bool(rendered_asset_ids),
        },
        "assets": list(rendered_assets.values()),
        "asset_ids": rendered_asset_ids,
        "rendered_asset_ids": rendered_asset_ids,
        "render_allowed_asset_ids": render_allowed_asset_ids,
        "attribution_receipt": attribution_receipts,
        "attribution_receipt_hash": canonical_hash({"items": attribution_receipts}),
        "compliance_result": {
            "schema_version": "card_news_compliance.v1",
            "package_id": compliance_id,
            "status": "valid" if not blockers else "blocked",
            "publish_ready": not blockers,
            "blocking_reasons": blockers,
        },
        "provenance": {
            "source": "ProductionController",
            "controller_id": _text(controller_state.get("controller_id")),
            "state_hash": _text(controller_state.get("state_hash")),
            "render_manifest_hash": canonical_hash(render_manifest),
        },
        "technical_fixture_not_publish_approved": False,
        "release_guard": {"ready": not blockers, "issue_codes": blockers},
        "actual_publish": False,
        "upload_executed": False,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ready_for_publishing_module" if not blockers else "blocked",
        "reason_code": (
            "controller_owner_approved_handoff_built"
            if not blockers
            else "release_handoff_blocked"
        ),
        "title": title,
        "output_set_id": output_set_id,
        "cards": [{"card_path": card["path"], "index": card["index"]} for card in cards],
        "image_sourcing_status": {
            "manual_image_required": False,
            "real_image_used_count": len(rendered_asset_ids),
            "rendered_visual_asset_count": len(rendered_asset_ids),
            "checklist": [],
        },
        "pre_publish_attestation": attestation,
        "actual_publish": False,
        "publish_executed": False,
        "upload_executed": False,
    }


__all__ = ["build_production_release_handoff", "SCHEMA_VERSION"]
