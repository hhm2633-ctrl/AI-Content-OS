"""Affiliate Revenue Router Phase 1 -- program, offer, and pairing gates.

Every function here is a pure, deterministic decision: given a normalized
`AffiliateProgram`/`MerchantOffer`/`RoutingRequest` (see
`affiliate_contract.py`), return `(status, reasons)` where `status` is one of
`affiliate_result.STATUS_ELIGIBLE/STATUS_MANUAL_REVIEW/STATUS_REJECTED` and
`reasons` is a list of `{"scope", "code", "message"}` dicts.

No network I/O. No LLM judgment. Reasons never quote raw URL/offer content --
only field names, codes, and fixed template text -- so a secret embedded in a
URL can never leak through a gate's own diagnostic message.

Design basis: `docs/RESEARCH/AFFILIATE/AFFILIATE_NETWORK_EVIDENCE_MATRIX.md`.
Freshness windows below are this module's own conservative operational
defaults (loosely following that document's `PROPOSED` freshness table,
Section 6) -- they are not a claim about any network's actual guarantee.

NO-GO fixes in this pass:
- An unregistered network (absent from `NETWORK_CAPABILITY_CEILING`) is now
  capped at `"unknown"` by default -- a self-declared `"confirmed"` for a
  network the evidence matrix never classified is always ignored.
- Even a registered, `"confirmed"`-ceiling network (Linkprice/Adpick) cannot
  reach `eligible` on API existence alone -- it must *also* have complete
  `enrollment` evidence (`_enrollment_evidence_complete`); missing/incomplete
  enrollment evidence degrades the result to `manual_review`, never a hard
  reject (a human can still supply it).
- `policy_checked_at` and `source_timestamp` in the future are rejected
  outright, not merely treated as "not stale".
- A network's `policy_evidence_url` is checked against a confirmed official
  domain allowlist when one exists for that network; an unlisted network has
  no enforceable domain (never invented) and is not checked this way.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from modules.affiliate.affiliate_result import STATUS_ELIGIBLE, STATUS_MANUAL_REVIEW, STATUS_REJECTED, ALLOWED_RIGHTS_STATUSES
from modules.affiliate.affiliate_safety_utils import extract_hostname, is_safe_public_url, parse_tz_datetime

# "우선 프로그램 처리" -- Phase 1 capability ceiling per the official evidence
# matrix. A declared `api_status` is capped DOWN to this ceiling; it is never
# raised above it. A network absent from this table defaults to the
# `_DEFAULT_CEILING_FOR_UNLISTED_NETWORKS` ceiling below (NO-GO fix) -- it is
# never left uncapped.
NETWORK_CAPABILITY_CEILING: Dict[str, str] = {
    "linkprice": "confirmed",              # POC GO 1 -- domestic product affiliate
    "adpick": "confirmed",                 # POC GO 2 -- domestic product affiliate
    "naver_shopping_connect": "manual_only",  # human-assisted only, per evidence matrix Section 4.3
    "impact": "manual_only",               # deferred global network, high policy risk, per Section 4.4
    "tos": "unknown",                      # identity unresolved -- never guessed, per evidence matrix
}

# NO-GO fix: a network absent from `NETWORK_CAPABILITY_CEILING` above is not
# left un-capped -- it defaults to this ceiling, so a self-declared
# `"confirmed"` for an unregistered network is always ignored.
_DEFAULT_CEILING_FOR_UNLISTED_NETWORKS = "unknown"

# NO-GO fix (rule 14): confirmed official policy/evidence domains per
# network, from the evidence matrix's own cited URLs. A network absent from
# this table has no confirmed domain to check against -- this module never
# invents one; the generic `is_safe_public_url` check still applies.
NETWORK_POLICY_DOMAIN_ALLOWLIST: Dict[str, Tuple[str, ...]] = {
    "linkprice": ("linkprice.com",),
    "adpick": ("adpick.co.kr",),
    "naver_shopping_connect": ("brandconnect.naver.com",),
    "impact": ("help.impact.com",),
}

API_STATUS_RANK = {"blocked": 0, "unknown": 1, "manual_only": 2, "confirmed": 3}
_RANK_TO_API_STATUS = {rank: status for status, rank in API_STATUS_RANK.items()}

POLICY_MAX_AGE = timedelta(days=30)
PRICE_MAX_AGE = timedelta(hours=6)
STOCK_MAX_AGE = timedelta(hours=1)
COMMISSION_MAX_AGE = timedelta(hours=24)

_KNOWN_PROGRAM_TYPES_FOR_ROUTING = {"product_affiliate", "global_retail", "global_network"}
_KNOWN_AVAILABILITY_VALUES = {"in_stock", "out_of_stock", "preorder"}


def _normalize_network_id(network_id: str) -> str:
    return str(network_id or "").strip().lower().replace(" ", "_").replace("-", "_")


def effective_api_status(network_id: str, declared_status: str) -> Tuple[str, bool]:
    """Return `(effective_status, ceiling_applied)`.

    `declared_status` is assumed already normalized to one of the four known
    values by `affiliate_contract.py` (an unrecognized value already becomes
    `"unknown"` there -- fail-closed before this function ever runs).
    """
    ceiling = NETWORK_CAPABILITY_CEILING.get(_normalize_network_id(network_id), _DEFAULT_CEILING_FOR_UNLISTED_NETWORKS)

    declared_rank = API_STATUS_RANK.get(declared_status, API_STATUS_RANK["unknown"])
    ceiling_rank = API_STATUS_RANK[ceiling]
    effective_rank = min(declared_rank, ceiling_rank)
    return _RANK_TO_API_STATUS[effective_rank], effective_rank < declared_rank


def _enrollment_evidence_complete(enrollment: Dict[str, Any]) -> bool:
    """NO-GO fix (rules 9/10): every boolean sub-field must be an actual
    `bool` `True` (see `affiliate_contract.py::_clean_bool` -- a string
    `"true"`/`1`/etc. never counts), and `evidence_checked_at` must be a
    parseable, timezone-aware date/time."""
    checked_at = parse_tz_datetime(enrollment.get("evidence_checked_at"))
    return (
        enrollment.get("account_access_confirmed") is True
        and enrollment.get("merchant_enrollment_confirmed") is True
        and enrollment.get("product_enrollment_confirmed") is True
        and enrollment.get("channel_allowed_confirmed") is True
        and checked_at is not None
    )


def _policy_domain_allowed(network_id: str, url: str) -> bool:
    allowed_domains = NETWORK_POLICY_DOMAIN_ALLOWLIST.get(_normalize_network_id(network_id))
    if allowed_domains is None:
        return True  # no confirmed allowlist for this network -- never invented

    hostname = extract_hostname(url)
    if not hostname:
        return False
    return any(hostname == domain or hostname.endswith("." + domain) for domain in allowed_domains)


def _reason(scope: str, code: str, message: str) -> Dict[str, str]:
    return {"scope": scope, "code": code, "message": message}


def evaluate_program(program: Dict[str, Any], request: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]]]:
    """Evaluate one `AffiliateProgram` against the routing request's context.

    Never depends on any specific offer -- see `evaluate_pairing` for the one
    program<->offer cross-check (currency).
    """
    reasons: List[Dict[str, str]] = []

    if program["program_type"] == "lead_cpa":
        return STATUS_REJECTED, [_reason("program", "lead_cpa_blocked", "lead_cpa program types are always blocked in the Phase 1 product-affiliate router.")]

    if program["program_type"] not in _KNOWN_PROGRAM_TYPES_FOR_ROUTING:
        reasons.append(_reason("program", "program_type_unrecognized", "program_type is not a recognized product-affiliate type; manual review required."))

    effective_status, ceiling_applied = effective_api_status(program["network_id"], program["api_status"])

    if effective_status == "blocked":
        return STATUS_REJECTED, reasons + [_reason("program", "api_status_blocked", "Program api_status resolves to blocked.")]
    if effective_status == "unknown":
        return STATUS_REJECTED, reasons + [_reason("program", "api_status_unknown", "Program api_status resolves to unknown; excluded pending identity/policy proof.")]
    if effective_status == "manual_only":
        code = "api_status_manual_only_capability_capped" if ceiling_applied else "api_status_manual_only"
        reasons.append(_reason("program", code, "Program requires human-assisted link issuance; returned as a manual-review candidate only."))

    if not program["policy_version"] or not program["policy_evidence_url"] or not program["policy_checked_at"]:
        reasons.append(_reason("program", "policy_metadata_incomplete", "policy_version, policy_evidence_url, and policy_checked_at must all be present."))
    else:
        if program["policy_evidence_url"] and not is_safe_public_url(program["policy_evidence_url"]):
            return STATUS_REJECTED, reasons + [_reason("program", "unsafe_policy_evidence_url", "policy_evidence_url is not a safe, credential-free public URL.")]

        if program["policy_evidence_url"] and not _policy_domain_allowed(program["network_id"], program["policy_evidence_url"]):
            return STATUS_REJECTED, reasons + [_reason("program", "policy_evidence_domain_mismatch", "policy_evidence_url's domain does not match this network's confirmed official domain.")]

        checked_at = parse_tz_datetime(program["policy_checked_at"])
        if checked_at is None:
            reasons.append(_reason("program", "policy_checked_at_invalid_timezone", "policy_checked_at must be a timezone-aware date/time value."))
        else:
            current_time = request["current_time"]
            if isinstance(current_time, datetime):
                if checked_at > current_time:
                    return STATUS_REJECTED, reasons + [_reason("program", "policy_checked_at_future", "policy_checked_at is in the future.")]
                if current_time - checked_at > POLICY_MAX_AGE:
                    reasons.append(_reason("program", "policy_stale", f"policy_checked_at is older than the allowed {POLICY_MAX_AGE.days} days."))

    if request["channel"] and program["allowed_channels"] and request["channel"] not in program["allowed_channels"]:
        return STATUS_REJECTED, reasons + [_reason("program", "channel_not_allowed", "Requested channel is not in the program's allowed_channels.")]

    if request["region"] and program["region"] and request["region"] != program["region"]:
        return STATUS_REJECTED, reasons + [_reason("program", "region_mismatch", "Program region does not match the routing request's region.")]

    if request["category"] and request["category"] in program["restricted_categories"]:
        return STATUS_REJECTED, reasons + [_reason("program", "restricted_category", "Requested category is in the program's restricted_categories.")]

    if not _enrollment_evidence_complete(program["enrollment"]):
        # NO-GO fix (rules 8/9/10): API/network capability alone is never
        # enough -- confirmed enrollment evidence is required to reach
        # `eligible`; missing/incomplete evidence is a manual-review signal,
        # not an outright rejection (a human can still supply it).
        reasons.append(_reason("program", "enrollment_evidence_incomplete", "account_access_confirmed, merchant_enrollment_confirmed, product_enrollment_confirmed, channel_allowed_confirmed, and a timezone-aware evidence_checked_at are all required."))

    # Every code that can still be in `reasons` at this point (unrecognized
    # program_type, manual_only api_status, incomplete/stale/invalid policy
    # metadata, incomplete enrollment evidence) is a manual-review signal, not
    # an outright rejection -- those were already returned early above. An
    # empty list means every gate passed cleanly.
    return (STATUS_MANUAL_REVIEW if reasons else STATUS_ELIGIBLE), reasons


def evaluate_offer(offer: Dict[str, Any], request: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]], bool]:
    """Evaluate one `MerchantOffer` against the routing request's context.

    Returns `(status, reasons, image_usage_approved)`. `image_usage_approved`
    reflects `rights_status` only (whether the *image* may be used) -- it is
    never a signal of program-enrollment approval (NO-GO fix, rule 23).
    """
    reasons: List[Dict[str, str]] = []

    for field_name, code in (("canonical_url", "unsafe_canonical_url"), ("source_url", "unsafe_source_url"), ("image_url", "unsafe_image_url")):
        value = offer.get(field_name)
        if value and not is_safe_public_url(value):
            return STATUS_REJECTED, [_reason("offer", code, f"{field_name} is not a safe, credential-free public URL.")], False

    if request["region"] and offer["region"] and request["region"] != offer["region"]:
        return STATUS_REJECTED, [_reason("offer", "offer_region_mismatch", "Offer region does not match the routing request's region.")], False

    if request["category"] and offer["category"] and request["category"] != offer["category"]:
        return STATUS_REJECTED, [_reason("offer", "offer_category_mismatch", "Offer category does not match the routing request's category.")], False

    volatile_present = offer["price"] is not None or offer["availability"] or offer["commission_value"] is not None
    source_timestamp = parse_tz_datetime(offer["source_timestamp"])

    if volatile_present and (not offer["source_url"] or source_timestamp is None):
        if offer["source_url"] and source_timestamp is None and offer["source_timestamp"]:
            reasons.append(_reason("offer", "source_timestamp_invalid_timezone", "source_timestamp must be a timezone-aware date/time value."))
        else:
            reasons.append(_reason("offer", "source_evidence_missing", "price/availability/commission require both source_url and a valid source_timestamp."))

    current_time = request["current_time"]
    if source_timestamp is not None and isinstance(current_time, datetime):
        if source_timestamp > current_time:
            # NO-GO fix: a future-dated evidence timestamp is rejected
            # outright, not merely treated as "not stale".
            return STATUS_REJECTED, reasons + [_reason("offer", "source_timestamp_future", "source_timestamp is in the future.")], False

        age = current_time - source_timestamp
        if offer["price"] is not None and age > PRICE_MAX_AGE:
            reasons.append(_reason("offer", "price_stale", f"price evidence is older than the allowed {PRICE_MAX_AGE}."))
        if offer["availability"] and age > STOCK_MAX_AGE:
            reasons.append(_reason("offer", "availability_stale", f"availability evidence is older than the allowed {STOCK_MAX_AGE}."))
        if offer["commission_value"] is not None and age > COMMISSION_MAX_AGE:
            reasons.append(_reason("offer", "commission_stale", f"commission evidence is older than the allowed {COMMISSION_MAX_AGE}."))

    valid_from = parse_tz_datetime(offer["valid_from"])
    valid_until = parse_tz_datetime(offer["valid_until"])

    if offer["valid_until"] and valid_until is None:
        reasons.append(_reason("offer", "offer_validity_timezone_invalid", "valid_until must be a timezone-aware date/time value."))
    elif valid_until is not None and isinstance(current_time, datetime) and current_time > valid_until:
        return STATUS_REJECTED, reasons + [_reason("offer", "offer_expired", "The offer's valid_until has already passed.")], False

    if offer["valid_from"] and valid_from is None:
        reasons.append(_reason("offer", "offer_validity_timezone_invalid", "valid_from must be a timezone-aware date/time value."))
    elif valid_from is not None and isinstance(current_time, datetime) and current_time < valid_from:
        return STATUS_REJECTED, reasons + [_reason("offer", "offer_not_yet_valid", "The offer's valid_from is in the future.")], False

    if offer["availability"] == "out_of_stock":
        return STATUS_REJECTED, reasons + [_reason("offer", "offer_out_of_stock", "Offer availability is out_of_stock.")], False
    if offer["availability"] not in _KNOWN_AVAILABILITY_VALUES:
        reasons.append(_reason("offer", "availability_unknown", "Offer availability is not confirmed; it must not be represented as purchasable."))

    # rule 23: rights_status means image-usage permission only -- it is never
    # read anywhere as program-enrollment approval.
    image_usage_approved = offer["rights_status"] in ALLOWED_RIGHTS_STATUSES
    if not image_usage_approved:
        reasons.append(_reason("offer", "image_rights_unconfirmed", "rights_status is missing or not in the allowed set; image usage is not approved."))

    # Every remaining code (stale evidence, missing source, unconfirmed
    # availability, unconfirmed image rights, invalid validity timezone) is a
    # manual-review signal -- outright rejections already returned above.
    status = STATUS_MANUAL_REVIEW if reasons else STATUS_ELIGIBLE
    return status, reasons, image_usage_approved


def evaluate_pairing(program: Dict[str, Any], offer: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]]]:
    """The one program<->offer cross-check Phase 1 needs: currency match.

    The network_id/program_id/merchant_id back-reference match is enforced
    upstream in `affiliate_revenue_router.py` (an offer is never evaluated
    against a program it does not exactly reference), so it is not repeated
    here.
    """
    if program["currency"] and offer["currency"] and program["currency"] != offer["currency"]:
        return STATUS_REJECTED, [_reason("pairing", "currency_mismatch", "Offer currency does not match the program's currency.")]
    return STATUS_ELIGIBLE, []
