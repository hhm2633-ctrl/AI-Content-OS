"""Defensive input contract for the networkless BrandConnect Phase 1 lane."""

from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "brandconnect_phase_1.v1"
MODES = frozenset({"creator_campaign", "shopping_connect"})
ALLOWED_RIGHTS_STATUSES = frozenset({
    "owned", "licensed", "public_domain", "official_reuse_allowed",
    "user_supplied_with_permission",
})
RECEIPT_FIELDS = ("status", "schema_version", "receipt_id", "input_hash", "checked_at", "issuer", "trusted")


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _text_list(value: Any) -> List[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [_text(item) for item in value if _text(item)]


def _bool(value: Any) -> bool:
    return value if isinstance(value, bool) else False


def _nonnegative_int(value: Any) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _mapping(value: Any) -> Dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def _receipt(value: Any) -> Dict[str, Any]:
    raw = _mapping(value)
    return {
        "status": _text(raw.get("status")).lower(),
        "schema_version": _text(raw.get("schema_version")),
        "receipt_id": _text(raw.get("receipt_id")),
        "input_hash": _text(raw.get("input_hash")),
        "checked_at": raw.get("checked_at"),
        "issuer": _text(raw.get("issuer")).lower(),
        "trusted": _bool(raw.get("trusted")),
    }


def opaque_request_id(value: Any) -> str:
    """Never echo caller identifiers; return a stable irreversible correlation token."""
    text = value if isinstance(value, str) else ""
    return "bc_" + hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:20]


def _normalize_campaign_brief(raw: Any) -> Dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    return {
        "campaign_id": _text(raw.get("campaign_id")),
        "title": _text(raw.get("title")),
        "required_keywords": _text_list(raw.get("required_keywords")),
        "required_keyword_count": _nonnegative_int(raw.get("required_keyword_count")),
        "required_images": _nonnegative_int(raw.get("required_images")),
        "required_video": _bool(raw.get("required_video")),
        "required_map": _bool(raw.get("required_map", raw.get("required_map_or_place"))),
        "required_links": _text_list(raw.get("required_links")),
        "required_link": _bool(raw.get("required_link")) or bool(_text_list(raw.get("required_links"))),
        "required_disclosure": (
            raw.get("required_disclosure")
            if isinstance(raw.get("required_disclosure"), bool) else True
        ),
        "disclosure_text": _text(raw.get("disclosure_text")),
        "deadline": raw.get("deadline"),
        "compensation": _mapping(raw.get("compensation")),
        "terms_confirmed": _bool(raw.get("terms_confirmed")),
        "instructions": _text_list(raw.get("instructions")),
    }


def _normalize_product(raw: Any) -> Dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    return {
        "product_id": _text(raw.get("product_id")),
        "smartstore_product_id": _text(raw.get("smartstore_product_id")),
        "name": _text(raw.get("name")),
        "category": _text(raw.get("category")).lower(),
        "product_status": _text(raw.get("product_status")).lower(),
        "configured_commission": deepcopy(raw.get("configured_commission")),
        "configured_use_fee": deepcopy(raw.get("configured_use_fee")),
        "checked_at": raw.get("checked_at"),
        "source_ref": _text(raw.get("source_ref")),
    }


def normalize_brandconnect_request(raw: Any) -> Dict[str, Any]:
    """Return a new JSON-oriented mapping without mutating caller-owned input."""
    # The initial copy is part of the public boundary: hostile mapping subclasses or
    # deepcopy hooks must fail before any caller-owned object is inspected further.
    raw = deepcopy(raw) if isinstance(raw, dict) else {}
    policy = _mapping(raw.get("policy_context"))
    content = _mapping(raw.get("content"))
    link = _mapping(raw.get("manual_link"))
    approvals = _mapping(raw.get("approvals"))
    creator_compensation = _mapping(raw.get("creator_compensation")) or _mapping(raw.get("compensation"))
    affiliate_commission = _mapping(raw.get("affiliate_commission")) or _mapping(raw.get("affiliate"))
    return {
        "schema_version": SCHEMA_VERSION,
        "request_id": opaque_request_id(raw.get("request_id")),
        "mode": _text(raw.get("mode")).lower(),
        "channel": _text(raw.get("channel")).lower(),
        "category": _text(raw.get("category")).lower(),
        "campaign_brief": _normalize_campaign_brief(raw.get("campaign_brief")),
        "creator": _mapping(raw.get("creator")),
        "seller": _mapping(raw.get("seller")),
        "product": _normalize_product(raw.get("product")),
        "creator_compensation": creator_compensation,
        "affiliate_commission": affiliate_commission,
        # Compatibility aliases used by the package boundary; values remain separate.
        "compensation": deepcopy(creator_compensation),
        "affiliate": deepcopy(affiliate_commission),
        "content": {
            "title": _text(content.get("title")),
            "body": _text(content.get("body")),
            "claims": deepcopy(content.get("claims")) if isinstance(content.get("claims"), list) else [],
            "contains_pii": _bool(content.get("contains_pii")),
            "rights_status": _text(content.get("rights_status")).lower(),
            "disclosure_text": _text(content.get("disclosure_text")),
            "stats_external_disclosure": _bool(content.get("stats_external_disclosure")),
            "manual_pii_review": _bool(content.get("manual_pii_review")),
            "manual_claim_review": _bool(content.get("manual_claim_review")),
            "manual_traffic_review": _bool(content.get("manual_traffic_review")),
        },
        "manual_link": {
            "attached": _bool(link.get("attached")) or _bool(approvals.get("human_link_attached")),
            # Opaque value: deliberately preserve the exact Python string.
            "url": link.get("url") if isinstance(link.get("url"), str) else "",
            "generated_in": _text(link.get("generated_in")),
            "link_source": _text(link.get("link_source")) or _text(link.get("generated_in")),
            "attached_by": _text(link.get("attached_by")),
            "attached_at": link.get("attached_at"),
            "owner_scope": _text(link.get("owner_scope")),
            "owner_creator_id": _text(link.get("owner_creator_id")),
            "owner_product_id": _text(link.get("owner_product_id")),
            "tamper_checked": _bool(link.get("tamper_checked")),
            "disclosure_present": _bool(link.get("disclosure_present")),
            "cross_product_reuse": _bool(link.get("cross_product_reuse", link.get("reused_product"))),
            "cross_creator_reuse": _bool(link.get("cross_creator_reuse", link.get("reused_creator"))),
            "generated_sub_id": _bool(link.get("generated_sub_id")),
            "generated_hash": _bool(link.get("generated_hash")),
            "tampered": _bool(link.get("tampered")),
        },
        "traffic": {
            "abnormal": _bool(_mapping(raw.get("traffic")).get("abnormal")),
            "rewarded_click": _bool(_mapping(raw.get("traffic")).get("rewarded_click")),
        },
        "policy_context": {
            "api_status": _text(policy.get("api_status")).lower() or "unknown",
            "policy_version": _text(policy.get("policy_version")),
            "policy_evidence_urls": _text_list(policy.get("policy_evidence_urls")),
            "checked_at": policy.get("checked_at"),
            "allowed_channels": [v.lower() for v in _text_list(policy.get("allowed_channels"))],
            "restricted_channels": [v.lower() for v in _text_list(policy.get("restricted_channels"))],
            "restricted_categories": [v.lower() for v in _text_list(policy.get("restricted_categories"))],
        },
        "compliance_ready": _bool(raw.get("compliance_ready")) or _bool(approvals.get("compliance_ready")),
        "affiliate_ready": _bool(raw.get("affiliate_ready")) or _bool(approvals.get("affiliate_ready")),
        "human_approval": _bool(raw.get("human_approval")) or _bool(approvals.get("human_approval")),
        "approvals": {
            "compliance_ready": _bool(raw.get("compliance_ready")) or _bool(approvals.get("compliance_ready")),
            "affiliate_ready": _bool(raw.get("affiliate_ready")) or _bool(approvals.get("affiliate_ready")),
            "human_link_attached": _bool(link.get("attached")) or _bool(approvals.get("human_link_attached")),
            "human_approval": _bool(raw.get("human_approval")) or _bool(approvals.get("human_approval")),
        },
        "receipts": {
            "compliance": _receipt(raw.get("compliance_receipt") or approvals.get("compliance_receipt")),
            "affiliate": _receipt(raw.get("affiliate_receipt") or approvals.get("affiliate_receipt")),
            "human": _receipt(raw.get("human_approval_receipt") or approvals.get("human_approval_receipt")),
            "disclosure": _receipt(raw.get("disclosure_receipt") or approvals.get("disclosure_receipt")),
        },
        "current_time": raw.get("current_time"),
    }


class BrandConnectContract:
    normalize = staticmethod(normalize_brandconnect_request)
