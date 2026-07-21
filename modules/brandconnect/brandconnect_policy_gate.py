"""Pure, fail-closed BrandConnect policy gate; no network or publish actions."""

from __future__ import annotations

import ipaddress
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .brandconnect_contract import ALLOWED_RIGHTS_STATUSES, MODES, normalize_brandconnect_request

POLICY_RECHECK_DAYS = 30
OFFICIAL_UI = "naver_brandconnect_ui"
DEFAULT_DISCLOSURE = "이 포스팅은 네이버 쇼핑 커넥트 활동의 일환으로, 판매 발생 시 수수료를 제공받습니다."
_NAVER_OPAQUE_LINK = re.compile(r"^https://naver\.me/[^\s/?#][^\s?#]*$", re.ASCII)
UPSTREAM_INTEGRATION_GO = False
APPROVED_RECEIPTS = {
    "compliance": ("campaign_compliance_phase_1", "passed", "campaign_compliance_phase_1.v1"),
    "affiliate": ("affiliate_revenue_router_phase_1", "routed", "affiliate_revenue_router_phase_1.v1"),
    "human": ("brandconnect_human_approval", "approved", "brandconnect_human_approval.v1"),
    "disclosure": ("brandconnect_disclosure_review", "approved", "brandconnect_disclosure_review.v1"),
}
_PII_PATTERNS = (
    re.compile(r"(?<!\d)01[016789][- ]?\d{3,4}[- ]?\d{4}(?!\d)"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(?<!\d)\d{6}[- ]?[1-4]\d{6}(?!\d)"),
)
_CLAIM_PATTERN = re.compile(r"(무조건|완치|100\s*%|최고|유일|확실한?\s*수익|보장(?:된|합니다)?|절대)" , re.I)
_REWARDED_PATTERN = re.compile(r"(클릭|구매).{0,20}(보상|리워드|캐시|포인트|추첨|지급)|(?:보상|리워드|캐시|포인트).{0,20}(클릭|구매)", re.I)


def _aware_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo and value.utcoffset() is not None else None
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.astimezone(timezone.utc) if parsed.tzinfo and parsed.utcoffset() is not None else None
    return None


def _safe_public_url(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = urlparse(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return False
        host = parsed.hostname.rstrip(".").lower()
        if host == "localhost" or host.endswith(".localhost"):
            return False
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return True
        return not any((address.is_private, address.is_loopback, address.is_link_local,
                        address.is_reserved, address.is_unspecified))
    except (ValueError, UnicodeError):
        return False


def _valid_opaque_naver_link(value: Any) -> bool:
    """Validate syntax only; never resolve, expand, request, or inspect query data."""
    if not isinstance(value, str) or _NAVER_OPAQUE_LINK.fullmatch(value) is None:
        return False
    try:
        parsed = urlparse(value)
        return bool(parsed.path and parsed.path != "/" and not parsed.query and not parsed.fragment
                    and not parsed.username and not parsed.password and parsed.port is None)
    except (ValueError, UnicodeError):
        return False


def _valid_receipt(kind: str, receipt: Dict[str, Any], current: datetime) -> bool:
    issuer, status, schema = APPROVED_RECEIPTS[kind]
    checked = _aware_datetime(receipt.get("checked_at"))
    return bool(receipt.get("trusted") is True and receipt.get("issuer") == issuer
                and receipt.get("status") == status and receipt.get("schema_version") == schema
                and receipt.get("receipt_id") and receipt.get("input_hash")
                and checked is not None and checked <= current)


def _reason(code: str, message: str) -> Dict[str, str]:
    return {"code": code, "message": message}


def _evaluate_brandconnect_policy(raw: Any, now: Any = None) -> Dict[str, Any]:
    request = normalize_brandconnect_request(raw)
    blocking: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    policy = request["policy_context"]
    brief = request["campaign_brief"]
    content = request["content"]
    current = _aware_datetime(now if now is not None else request.get("current_time"))
    if current is None:
        current = datetime.now(timezone.utc)
        blocking.append(_reason("current_time_invalid_timezone", "A timezone-aware current_time is required."))

    if request["mode"] not in MODES:
        blocking.append(_reason("unsupported_mode", "mode must be creator_campaign or shopping_connect."))
    if policy["api_status"] != "manual_only":
        blocking.append(_reason("brandconnect_api_unknown", "No public BrandConnect automation API is confirmed; manual-only handling is required."))
    if not brief["campaign_id"] or not brief["terms_confirmed"]:
        blocking.append(_reason("missing_campaign_terms", "Campaign identity and confirmed terms are required."))

    creator = request["creator"]
    seller = request["seller"]
    product = request["product"]
    if not str(creator.get("creator_id", "")).strip() or not str(creator.get("ownership_evidence_id", "")).strip():
        blocking.append(_reason("creator_identity_ownership_missing", "Creator identity and ownership evidence are required."))
    if not str(seller.get("seller_id", "")).strip() or not str(seller.get("ownership_evidence_id", "")).strip():
        blocking.append(_reason("seller_identity_ownership_missing", "Seller identity and ownership evidence are required."))
    if not (product["product_id"] or product["smartstore_product_id"]) or not product["source_ref"]:
        blocking.append(_reason("product_identity_ownership_missing", "Product identity and source ownership evidence are required."))

    checked = _aware_datetime(policy.get("checked_at"))
    recheck_required = checked is None or current - checked > timedelta(days=POLICY_RECHECK_DAYS)
    if checked is None:
        blocking.append(_reason("policy_checked_at_invalid", "Policy checked_at must include a timezone."))
    elif checked > current:
        blocking.append(_reason("policy_checked_at_future", "Policy checked_at cannot be in the future."))
    elif recheck_required:
        blocking.append(_reason("policy_recheck_required", "Policy evidence is older than the conservative 30-day window."))
    if not policy["policy_version"] or not policy["policy_evidence_urls"]:
        blocking.append(_reason("policy_metadata_incomplete", "Policy version and official evidence URLs are required."))
    elif any(not _safe_public_url(url) for url in policy["policy_evidence_urls"]):
        blocking.append(_reason("unsafe_policy_evidence_url", "Policy evidence must use safe public URLs."))

    channel = request["channel"]
    if channel in policy["restricted_channels"] or (policy["allowed_channels"] and channel not in policy["allowed_channels"]):
        blocking.append(_reason("restricted_channel", "The requested channel is not permitted by the supplied policy context."))
    if request["category"] in policy["restricted_categories"]:
        blocking.append(_reason("restricted_category", "The requested category is restricted."))
    combined_text = "\n".join((content["title"], content["body"], content["disclosure_text"]))
    if content["contains_pii"] or any(pattern.search(combined_text) for pattern in _PII_PATTERNS):
        blocking.append(_reason("pii_detected", "PII must be removed before handoff."))
    if not content["manual_pii_review"]:
        blocking.append(_reason("manual_pii_review_required", "A human PII review receipt is required."))
    if _CLAIM_PATTERN.search(combined_text):
        blocking.append(_reason("risky_claim_detected", "Potentially false or exaggerated wording requires removal."))
    if not content["manual_claim_review"]:
        blocking.append(_reason("manual_claim_review_required", "A human claims review is required."))
    if _REWARDED_PATTERN.search(combined_text):
        blocking.append(_reason("rewarded_click_text_detected", "Rewarded-click language is prohibited."))
    if not content["manual_traffic_review"]:
        blocking.append(_reason("manual_traffic_review_required", "A human traffic-inducement review is required."))
    if content["rights_status"] not in ALLOWED_RIGHTS_STATUSES:
        blocking.append(_reason("invalid_rights", "Asset/content rights are not confirmed."))

    claims = content["claims"]
    for claim in claims:
        if not isinstance(claim, dict):
            blocking.append(_reason("unverifiable_claim", "Every claim must have a structured evidence record."))
            continue
        if claim.get("false") is True or claim.get("exaggerated") is True:
            blocking.append(_reason("false_or_exaggerated_claim", "False or exaggerated claims are prohibited."))
        elif not claim.get("evidence_ref"):
            blocking.append(_reason("unverifiable_claim", "Claims require an evidence reference."))

    disclosure = content["disclosure_text"] or brief["disclosure_text"]
    if brief["required_disclosure"] and not disclosure:
        blocking.append(_reason("missing_disclosure", "Economic-interest disclosure text is required."))
    elif brief["required_disclosure"] and disclosure != DEFAULT_DISCLOSURE:
        blocking.append(_reason("disclosure_copy_unapproved", "The approved exact disclosure copy is required."))
    if content["stats_external_disclosure"]:
        blocking.append(_reason("stats_external_disclosure_prohibited", "BrandConnect statistics must not be disclosed externally."))
    if request["traffic"]["abnormal"] or request["traffic"]["rewarded_click"]:
        blocking.append(_reason("abnormal_traffic_prohibited", "Abnormal or rewarded-click traffic is prohibited."))

    for receipt_kind, receipt in request["receipts"].items():
        if not _valid_receipt(receipt_kind, receipt, current):
            blocking.append(_reason(f"{receipt_kind}_receipt_untrusted", "A complete approved, trusted, non-future receipt is required."))
    if not UPSTREAM_INTEGRATION_GO:
        blocking.append(_reason("upstream_integration_no_go", "Compliance and Affiliate upstream integrations remain NO-GO."))

    deadline = _aware_datetime(brief.get("deadline"))
    if brief.get("deadline") is not None and deadline is None:
        blocking.append(_reason("deadline_invalid_timezone", "Campaign deadline must include a timezone."))
    elif deadline is not None and deadline < current:
        blocking.append(_reason("campaign_deadline_expired", "Campaign deadline has expired."))

    link = request["manual_link"]
    if request["mode"] == "shopping_connect":
        if not link["attached"] or not link["url"]:
            blocking.append(_reason("missing_manual_link", "Attach a link issued manually in the BrandConnect UI."))
        elif not _valid_opaque_naver_link(link["url"]):
            blocking.append(_reason("invalid_manual_link_syntax", "The opaque link must use https://naver.me with a nonempty path."))
        if link["link_source"] != OFFICIAL_UI or link["tampered"] or not link["tamper_checked"]:
            blocking.append(_reason("link_tampering_or_origin_invalid", "The link must be unmodified and issued in the official BrandConnect UI."))
        attached_at = _aware_datetime(link["attached_at"])
        if not link["attached_by"] or attached_at is None:
            blocking.append(_reason("manual_link_receipt_incomplete", "attached_by and timezone-aware attached_at are required."))
        elif attached_at > current:
            blocking.append(_reason("manual_link_attached_at_future", "Manual link attached_at cannot be in the future."))
        creator_scope = str(request["creator"].get("owner_scope", "")).strip()
        account_scope = str(request["creator"].get("account_owner_scope", "")).strip()
        scopes = [scope for scope in (link["owner_scope"], creator_scope, account_scope) if scope]
        if len(set(scopes)) > 1:
            blocking.append(_reason("creator_account_owner_scope_mismatch", "Creator, account, and link owner scopes must match."))
        if not link["owner_scope"]:
            blocking.append(_reason("link_owner_scope_missing", "The opaque link requires an owner scope."))
        request_creator_id = str(request["creator"].get("creator_id", "")).strip()
        request_product_id = request["product"]["product_id"] or request["product"]["smartstore_product_id"]
        if request_creator_id and link["owner_creator_id"] != request_creator_id:
            blocking.append(_reason("creator_owner_mismatch", "The link owner creator must match the request creator."))
        if request_product_id and link["owner_product_id"] != request_product_id:
            blocking.append(_reason("product_owner_mismatch", "The link owner product must match the request product."))
        if link["cross_product_reuse"] or link["cross_creator_reuse"]:
            blocking.append(_reason("manual_link_reuse_prohibited", "A link reused across product or creator scope is prohibited."))
        if link["generated_sub_id"] or link["generated_hash"]:
            blocking.append(_reason("generated_tracking_identifier_prohibited", "Generated sub-ids or hashes are prohibited."))
        if not link["disclosure_present"]:
            blocking.append(_reason("manual_link_disclosure_missing", "The link receipt must confirm disclosure presence."))

    product_checked = _aware_datetime(request["product"].get("checked_at"))
    volatile_present = any(request["product"].get(key) not in (None, "") for key in (
        "product_status", "configured_commission", "configured_use_fee"))
    product_recheck_required = volatile_present and (
        product_checked is None or product_checked.year != current.year or product_checked.month != current.month
    )
    if product_checked is not None and product_checked > current:
        blocking.append(_reason("product_checked_at_future", "Product checked_at cannot be in the future."))
    if product_recheck_required:
        blocking.append(_reason("monthly_product_rate_recheck_required", "Product status and configured rates must be rechecked in the current month."))

    if not request["compliance_ready"]:
        blocking.append(_reason("compliance_not_ready", "Upstream compliance remains NO-GO or incomplete."))
    if not request["affiliate_ready"]:
        blocking.append(_reason("affiliate_not_ready", "Affiliate router readiness is not confirmed."))
    if not request["human_approval"]:
        blocking.append(_reason("human_approval_required", "Human approval is required before any publish-ready state."))

    human_link_attached = request["mode"] != "shopping_connect" or bool(link["attached"] and link["url"])
    publish_ready = bool(not blocking and UPSTREAM_INTEGRATION_GO and human_link_attached)
    return {
        "status": "pass" if publish_ready else "blocked",
        "blocking_reasons": blocking,
        "warnings": warnings,
        "checks": {
            "mode_valid": request["mode"] in MODES,
            "api_public_automation_confirmed": False,
            "disclosure_present": bool(disclosure),
            "rights_confirmed": content["rights_status"] in ALLOWED_RIGHTS_STATUSES,
            "stats_external_disclosure_prohibited": True,
            "traffic_normal": not (request["traffic"]["abnormal"] or request["traffic"]["rewarded_click"]),
            "policy_recheck_required": recheck_required,
            "product_rate_recheck_required": product_recheck_required,
        },
        "policy_receipts": [{
            "network": "naver_brandconnect",
            "api_status": "unknown",
            "effective_mode": "manual_only",
            "policy_version": policy["policy_version"] or "UNKNOWN",
            "checked_at": policy.get("checked_at"),
            "recheck_required": recheck_required,
            "product_rate_recheck_required": product_recheck_required,
            "stats_external_disclosure_prohibited": True,
        }],
        "disclosure_text": disclosure or DEFAULT_DISCLOSURE,
        "manual_link_required": request["mode"] == "shopping_connect",
        "link_generation_location": OFFICIAL_UI,
        "human_link_attached": human_link_attached,
        "link_receipt": {
            "manual_link_attached": bool(link["attached"] and link["url"]),
            "link_source": link["link_source"],
            "attached_by": link["attached_by"],
            "attached_at": link["attached_at"],
            "owner_scope": link["owner_scope"],
            "owner_creator_id": link["owner_creator_id"],
            "owner_product_id": link["owner_product_id"],
            "tamper_checked": link["tamper_checked"],
            "disclosure_present": link["disclosure_present"],
            # The opaque URL and any destination/tracking internals are intentionally omitted.
        },
        "publish_ready": publish_ready,
        "network_used": False,
        "actual_publish": False,
    }


def evaluate_brandconnect_policy(raw: Any, now: Any = None) -> Dict[str, Any]:
    """Exception-safe public boundary; never leak raw input, secrets, or exception text."""
    try:
        return _evaluate_brandconnect_policy(raw, now)
    except Exception:
        return {
            "status": "blocked", "blocking_reasons": [_reason(
                "brandconnect_internal_error", "BrandConnect validation could not complete safely.")],
            "warnings": [], "checks": {}, "policy_receipts": [],
            "disclosure_text": DEFAULT_DISCLOSURE, "manual_link_required": True,
            "link_generation_location": OFFICIAL_UI, "human_link_attached": False,
            "link_receipt": {}, "publish_ready": False, "network_used": False,
            "actual_publish": False,
        }


class BrandConnectPolicyGate:
    evaluate = staticmethod(evaluate_brandconnect_policy)
