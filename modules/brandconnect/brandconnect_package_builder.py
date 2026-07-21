"""Offline package builder for the human-assisted BrandConnect Phase-1 flow.

This module deliberately performs no login, link generation, network request, or
publication.  It converts the normalized contract and policy decision into
handoff packages that a human can review in Naver's own UI.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Dict, Mapping, Optional

from modules.brandconnect.brandconnect_contract import normalize_brandconnect_request
from modules.brandconnect.brandconnect_policy_gate import evaluate_brandconnect_policy


SCHEMA_VERSION = "brandconnect_phase_1.v1"
_UPSTREAM_INTEGRATION_APPROVED = False


def _mapping(value: Any) -> Dict[str, Any]:
    return deepcopy(dict(value)) if isinstance(value, Mapping) else {}


def _request_ref(value: Any) -> str:
    """Return a stable, irreversible correlation reference, never the raw id."""
    if not isinstance(value, str) or not value:
        return ""
    return "sha256:" + sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _financial_term_presence(value: Any) -> Dict[str, Any]:
    """Expose only safe provenance facts; financial input is never inferred/copied."""
    item = value if isinstance(value, Mapping) else {}
    return {
        "supplied": bool(item),
        "source_ref_present": bool(item.get("source_ref")) if item else False,
        "checked_at": item.get("checked_at") if item else None,
        "values_omitted_from_package": True,
    }


def _allowlist(value: Any, fields: tuple[str, ...]) -> Dict[str, Any]:
    item = value if isinstance(value, Mapping) else {}
    return {field: deepcopy(item.get(field)) for field in fields if field in item}


def _safe_brief(value: Any) -> Dict[str, Any]:
    brief = _allowlist(value, (
        "campaign_id", "title", "required_keywords", "required_keyword_count",
        "required_images", "required_video", "required_map", "required_links",
        "required_link", "required_disclosure", "disclosure_text", "deadline",
        "terms_confirmed", "instructions",
    ))
    source = value if isinstance(value, Mapping) else {}
    brief["compensation"] = _financial_term_presence(source.get("compensation"))
    return brief


def _safe_product(value: Any) -> Dict[str, Any]:
    product = _allowlist(value, (
        "product_id", "smartstore_product_id", "name", "category",
        "product_status", "checked_at", "source_ref",
    ))
    source = value if isinstance(value, Mapping) else {}
    product["configured_commission"] = _financial_term_presence(source.get("configured_commission"))
    product["configured_use_fee"] = _financial_term_presence(source.get("configured_use_fee"))
    return product


def _list(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple)):
        return deepcopy(list(value))
    if value in (None, ""):
        return []
    return [deepcopy(value)]


def _checklist(brief: Mapping[str, Any]) -> Dict[str, Any]:
    """Preserve requirements without inventing campaign quantities or terms."""
    return {
        "required_keywords": _list(brief.get("required_keywords")),
        "required_keyword_count": brief.get("required_keyword_count"),
        "required_images": brief.get("required_images"),
        "required_video": brief.get("required_video"),
        "required_map": brief.get("required_map"),
        "required_link": brief.get("required_link"),
        "required_disclosure": brief.get("required_disclosure"),
        "deadline": brief.get("deadline"),
        "compensation": deepcopy(brief.get("compensation")),
    }


def _manual_actions(mode: str, checklist: Mapping[str, Any]) -> list[Dict[str, Any]]:
    actions = [
        {
            "code": "human_review_required",
            "required": True,
            "location": "offline_review",
            "description": "캠페인 조건, 콘텐츠, 표시문구와 권리를 사람이 최종 확인합니다.",
        },
        {
            "code": "human_approval_required",
            "required": True,
            "location": "ai_content_os_review",
            "description": "게시 전 명시적인 사람의 승인을 기록합니다.",
        },
    ]
    if mode == "shopping_connect" or bool(checklist.get("required_link")):
        actions.append(
            {
                "code": "manual_link_required",
                "required": True,
                "manual_link_required": True,
                "link_generation_location": "naver_brandconnect_ui",
                "description": "네이버 브랜드커넥트 UI에서 사람이 링크를 발급하고 첨부합니다.",
            }
        )
    return actions


def _opaque_link_attachment(
    request: Mapping[str, Any], raw_request: Optional[Mapping[str, Any]] = None
) -> Dict[str, Any]:
    """Copy safe receipt facts only; never expose the opaque short URL.

    A BrandConnect short URL is an opaque platform value.  This function does
    not parse, expand, query, resolve, normalize, or derive tracking fields from
    it.  In particular destination URLs and NaPm/trx/hk-like metadata are never
    copied into the package.
    """
    normalized = request.get("manual_link")
    normalized = normalized if isinstance(normalized, Mapping) else {}
    return {
        "attached": bool(normalized.get("attached", False)),
        "link_source": normalized.get("link_source", normalized.get("generated_in", "")),
        "attached_by": normalized.get("attached_by", ""),
        "attached_at": normalized.get("attached_at"),
        "owner_scope": normalized.get("owner_scope", ""),
        "tamper_checked": bool(normalized.get("tamper_checked", False)),
        "disclosure_present": bool(normalized.get("disclosure_present", False)),
        "opaque_value_redacted": True,
        "expanded_or_resolved": False,
    }


def _unique_reasons(values: Any) -> list[Any]:
    """Deduplicate policy reasons while preserving structured reason codes."""
    result: list[Any] = []
    seen: set[tuple[str, str]] = set()
    for value in _list(values):
        if isinstance(value, Mapping):
            item = deepcopy(dict(value))
            key = (str(item.get("code", "")), str(item.get("message", "")))
        else:
            item = str(value)
            key = (item, "")
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _ledger_draft(request: Mapping[str, Any]) -> Dict[str, Any]:
    """Create an allowlisted lifecycle draft with no amounts or tracking data."""
    return {
        "draft_only": True,
        "request_ref": _request_ref(request.get("request_id")),
        "campaign_compensation": {
            "stream_type": "campaign_compensation",
            "status": "pending_approved_external_receipt",
            "amount_included": False,
        },
        "affiliate_commission": {
            "stream_type": "affiliate_commission",
            "status": "pending_approved_external_receipt",
            "amount_included": False,
        },
        "revenue_streams_separated": True,
        "events": [
            {"event_type": "purchase_confirmed", "status": "pending_external_input"},
            {"event_type": "cancelled", "status": "pending_external_input"},
            {"event_type": "returned", "status": "pending_external_input"},
            {"event_type": "settlement_confirmed", "status": "pending_external_input"},
        ],
        "actual_statistics_included": False,
        "actual_sales_included": False,
        "actual_settlement_included": False,
        "opaque_url_stored_in_ledger": False,
        "tracking_parameters_stored": False,
        "estimated_values_included": False,
    }


def _approval(request: Mapping[str, Any], key: str) -> bool:
    approvals = request.get("approvals")
    return bool(approvals.get(key, False)) if isinstance(approvals, Mapping) else False


def _result_from(
    request: Mapping[str, Any],
    policy: Mapping[str, Any],
    raw_request: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    mode = str(request.get("mode", ""))
    brief = _safe_brief(request.get("campaign_brief"))
    checklist = _checklist(brief)
    blocking = _list(policy.get("blocking_reasons"))
    warnings = _list(policy.get("warnings"))

    # Phase 1 cannot publish until the Compliance and Affiliate adapters have
    # independently passed QA and the integration constant is explicitly
    # changed in an approved integration change.
    blocking.append({
        "code": "upstream_integration_no_go",
        "message": "Compliance and Affiliate upstream integrations are not approved.",
    })
    publish_ready = False if not _UPSTREAM_INTEGRATION_APPROVED else bool(
        not blocking and policy.get("publish_ready") is True
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "request_ref": _request_ref(request.get("request_id")),
        "mode": mode,
        "creator_delivery_package": {
            "creator": _allowlist(request.get("creator"), (
                "creator_id", "owner_scope", "account_owner_scope", "ownership_evidence_ref",
            )),
            "channel": request.get("channel"),
            "category": request.get("category"),
            "campaign_brief": brief,
            "delivery_checklist": checklist,
            "campaign_compensation": _financial_term_presence(request.get("compensation")),
            "affiliate_commission": _financial_term_presence(request.get("affiliate")),
            "manual_link_attachment": _opaque_link_attachment(request, raw_request),
        },
        "seller_campaign_package": {
            "seller": _allowlist(request.get("seller"), (
                "seller_id", "smartstore_id", "owner_scope", "ownership_evidence_ref",
            )),
            "smartstore_product": _safe_product(request.get("product")),
            "configured_commission_or_use_fee": _financial_term_presence(request.get("affiliate")),
            "creator_campaign_brief": deepcopy(brief),
            "contract_separate_from_creator": True,
        },
        "manual_actions": _manual_actions(mode, checklist),
        "policy_receipts": _list(policy.get("policy_receipts")),
        "disclosure_text": str(policy.get("disclosure_text") or ""),
        "revenue_ledger_draft": _ledger_draft(request),
        "blocking_reasons": _unique_reasons(blocking),
        "warnings": _unique_reasons(warnings),
        "policy_checks": deepcopy(policy.get("checks", {})),
        "publish_ready": publish_ready,
        "manual_link_required": True,
        "link_generation_location": "naver_brandconnect_ui",
        "stats_external_disclosure_prohibited": True,
        "network_used": False,
        "actual_publish": False,
    }


def _failure(raw: Any) -> Dict[str, Any]:
    """Return a constant fail-closed shape without touching hostile input."""
    return {
        "schema_version": SCHEMA_VERSION,
        "request_ref": "",
        "mode": None,
        "creator_delivery_package": {},
        "seller_campaign_package": {},
        "manual_actions": [],
        "policy_receipts": [],
        "disclosure_text": "",
        "revenue_ledger_draft": {
            "draft_only": True,
            "actual_statistics_included": False,
            "opaque_url_stored_in_ledger": False,
            "tracking_parameters_stored": False,
            "estimated_values_included": False,
        },
        "blocking_reasons": ["internal_error_fail_closed"],
        "warnings": [],
        "policy_checks": {},
        "publish_ready": False,
        "manual_link_required": True,
        "link_generation_location": "naver_brandconnect_ui",
        "stats_external_disclosure_prohibited": True,
        "network_used": False,
        "actual_publish": False,
    }


def build_brandconnect_package(
    raw_request: Mapping[str, Any], *, now: Optional[datetime] = None
) -> Dict[str, Any]:
    """Build a JSON-safe, offline delivery package without mutating the input."""
    try:
        original = deepcopy(raw_request)
        normalized = normalize_brandconnect_request(original)
        decision = evaluate_brandconnect_policy(
            normalized, now=now or datetime.now(timezone.utc)
        )
        return _result_from(normalized, decision, original)
    except Exception:
        return _failure(None)


class BrandConnectPackageBuilder:
    """Small injectable facade for callers that prefer an object API."""

    def build(
        self, raw_request: Mapping[str, Any], *, now: Optional[datetime] = None
    ) -> Dict[str, Any]:
        return build_brandconnect_package(raw_request, now=now)
