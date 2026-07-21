"""Affiliate Revenue Router Phase 1 -- input contract normalization.

Defensive dict-in/dict-out normalization for `AffiliateProgram`,
`MerchantOffer`, and `RoutingRequest`. Every function reads the caller's raw
input via `.get()` only and builds brand-new dicts/lists -- the caller's
original objects are never mutated. No network I/O, no file I/O, no
credential handling.

NO-GO fixes in this pass:
- `MerchantOffer` now requires `network_id`/`program_id`/`merchant_id` back-
  references (the join key to `AffiliateProgram` -- see
  `affiliate_revenue_router.py`, which removed the old full Cartesian
  program*offer join in favor of exact back-reference matching).
- `AffiliateProgram` gained a structured `enrollment` block
  (`account_access_confirmed`/`merchant_enrollment_confirmed`/
  `product_enrollment_confirmed`/`channel_allowed_confirmed`/
  `evidence_checked_at`) -- every boolean sub-field is fail-closed to `False`
  unless it is an *actual* `bool` `True` (a string `"true"` or `1` does not
  count).
- `region` is normalized to uppercase everywhere (`AffiliateProgram`,
  `MerchantOffer`, `RoutingRequest`) so `"kr"`/`"KR"`/`"Kr"` compare equal.
- A duplicate program key (`network_id`+`program_id`+`merchant_id`) or a
  duplicate `offer_id` is now a **contract error** (`contract_errors`), not a
  silently-deduplicated warning -- the caller must refuse to route rather than
  guess which of two conflicting definitions "wins".
- `RoutingRequest` gained `disclosure_policy_verified` (bool, defaults
  `False` -- fail-closed, mirrors the existing `human_approval` default).
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from modules.affiliate.affiliate_safety_utils import safe_number

KNOWN_PROGRAM_TYPES = frozenset({
    "product_affiliate",
    "lead_cpa",
    "global_retail",
    "global_network",
})

KNOWN_API_STATUSES = frozenset({"confirmed", "manual_only", "unknown", "blocked"})


def _clean_str(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _clean_str_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if isinstance(item, (str, int, float)) and str(item).strip()]


def _clean_bool(value: Any) -> bool:
    """Fail-closed boolean coercion: only an actual `bool` `True` counts.

    NO-GO fix (fake enrollment-evidence type attack): a string `"true"`, the
    integer `1`, or any other truthy-looking non-bool value must never be
    treated as a confirmed enrollment condition.
    """
    return value is True


def _normalize_enrollment(raw: Any) -> Dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    return {
        "account_access_confirmed": _clean_bool(raw.get("account_access_confirmed")),
        "merchant_enrollment_confirmed": _clean_bool(raw.get("merchant_enrollment_confirmed")),
        "product_enrollment_confirmed": _clean_bool(raw.get("product_enrollment_confirmed")),
        "channel_allowed_confirmed": _clean_bool(raw.get("channel_allowed_confirmed")),
        "evidence_checked_at": raw.get("evidence_checked_at"),
    }


def normalize_affiliate_program(raw: Any) -> Dict[str, Any]:
    """Return a canonical `AffiliateProgram` dict. Never raises.

    `program_type` unrecognized values are preserved verbatim (the policy
    gate treats an unrecognized type as manual-review, never as
    `product_affiliate` by default). `api_status` collapses any value outside
    the known four-state vocabulary to `"unknown"` -- fail-closed, never a
    guessed `"confirmed"`.
    """
    raw = raw if isinstance(raw, dict) else {}

    api_status = _clean_str(raw.get("api_status")).lower()
    if api_status not in KNOWN_API_STATUSES:
        api_status = "unknown"

    return {
        "network_id": _clean_str(raw.get("network_id")),
        "program_id": _clean_str(raw.get("program_id")),
        "program_type": _clean_str(raw.get("program_type")).lower(),
        "merchant_id": _clean_str(raw.get("merchant_id")),
        "region": _clean_str(raw.get("region")).upper(),
        "currency": _clean_str(raw.get("currency")).upper(),
        "allowed_channels": [c.lower() for c in _clean_str_list(raw.get("allowed_channels"))],
        "restricted_categories": [c.lower() for c in _clean_str_list(raw.get("restricted_categories"))],
        "attribution_window": raw.get("attribution_window"),
        "policy_version": raw.get("policy_version") if isinstance(raw.get("policy_version"), str) and raw.get("policy_version").strip() else None,
        "policy_evidence_url": raw.get("policy_evidence_url") if isinstance(raw.get("policy_evidence_url"), str) and raw.get("policy_evidence_url").strip() else None,
        "policy_checked_at": raw.get("policy_checked_at"),
        "api_status": api_status,
        "enrollment": _normalize_enrollment(raw.get("enrollment")),
    }


def normalize_affiliate_programs(raw_list: Any) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Normalize a list of raw programs.

    A duplicate `(network_id, program_id, merchant_id)` key is a **contract
    error** (NO-GO fix), not a silently-deduplicated warning -- the caller
    must refuse to route the whole request rather than guess which
    definition should win.
    """
    if not isinstance(raw_list, list):
        return [], ["candidate_programs missing or not a list"]

    contract_errors: List[str] = []
    seen = set()
    clean: List[Dict[str, Any]] = []

    for index, raw in enumerate(raw_list):
        item = normalize_affiliate_program(raw)
        key = (item["network_id"], item["program_id"], item["merchant_id"])
        if key in seen:
            contract_errors.append(
                f"duplicate program (network_id={key[0]!r}, program_id={key[1]!r}, merchant_id={key[2]!r}) at index {index}"
            )
            continue
        seen.add(key)
        clean.append(item)

    return clean, contract_errors


def normalize_merchant_offer(raw: Any) -> Dict[str, Any]:
    """Return a canonical `MerchantOffer` dict. Never raises.

    `network_id`/`program_id`/`merchant_id` are the required back-reference
    to the `AffiliateProgram` this offer belongs to (NO-GO fix) -- an offer
    missing any of the three, or referencing a program that does not exist in
    the same request, is rejected by `affiliate_revenue_router.py` rather than
    matched against every candidate program.

    `price`/`commission_value` are coerced through `safe_number` -- a
    non-numeric, negative, `NaN`, or `Infinity` value silently becomes
    `None` (and is later treated as "no usable value", never as a crash or a
    trusted number for ranking).
    """
    raw = raw if isinstance(raw, dict) else {}

    return {
        "offer_id": _clean_str(raw.get("offer_id")),
        "network_id": _clean_str(raw.get("network_id")),
        "program_id": _clean_str(raw.get("program_id")),
        "merchant_id": _clean_str(raw.get("merchant_id")),
        "product_id": _clean_str(raw.get("product_id")),
        "title": _clean_str(raw.get("title")),
        "canonical_url": raw.get("canonical_url") if isinstance(raw.get("canonical_url"), str) else "",
        "image_url": raw.get("image_url") if isinstance(raw.get("image_url"), str) else "",
        "category": _clean_str(raw.get("category")).lower(),
        "region": _clean_str(raw.get("region")).upper(),
        "currency": _clean_str(raw.get("currency")).upper(),
        "price": safe_number(raw.get("price")),
        "availability": _clean_str(raw.get("availability")).lower(),
        "commission_type": _clean_str(raw.get("commission_type")).lower(),
        "commission_value": safe_number(raw.get("commission_value")),
        "valid_from": raw.get("valid_from"),
        "valid_until": raw.get("valid_until"),
        "source_url": raw.get("source_url") if isinstance(raw.get("source_url"), str) else "",
        "source_timestamp": raw.get("source_timestamp"),
        "rights_status": _clean_str(raw.get("rights_status")).lower(),
    }


def normalize_merchant_offers(raw_list: Any) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Normalize a list of raw offers.

    A duplicate `offer_id` is a **contract error** (NO-GO fix), not a
    silently-deduplicated warning.
    """
    if not isinstance(raw_list, list):
        return [], ["candidate_offers missing or not a list"]

    contract_errors: List[str] = []
    seen = set()
    clean: List[Dict[str, Any]] = []

    for index, raw in enumerate(raw_list):
        item = normalize_merchant_offer(raw)
        key = item["offer_id"] or f"unspecified_{index}"
        if key in seen:
            contract_errors.append(f"duplicate offer_id '{key}' at index {index}")
            continue
        seen.add(key)
        item["offer_id"] = key
        clean.append(item)

    return clean, contract_errors


def normalize_routing_request(raw: Any) -> Dict[str, Any]:
    """Return a canonical `RoutingRequest` dict plus accumulated contract errors.

    `human_approval`/`disclosure_policy_verified` are accepted and echoed
    back as explicit, required signals for `publish_ready` (see
    `affiliate_result.py::build_routing_result`) -- neither ever changes any
    per-candidate eligibility computation; they only gate the request-level
    `publish_ready` verdict.
    """
    raw = raw if isinstance(raw, dict) else {}

    programs, program_errors = normalize_affiliate_programs(raw.get("candidate_programs"))
    offers, offer_errors = normalize_merchant_offers(raw.get("candidate_offers"))

    return {
        "request_id": _clean_str(raw.get("request_id")),
        "channel": _clean_str(raw.get("channel")).lower(),
        "region": _clean_str(raw.get("region")).upper(),
        "category": _clean_str(raw.get("category")).lower(),
        "content_type": _clean_str(raw.get("content_type")),
        "candidate_programs": programs,
        "candidate_offers": offers,
        "current_time": raw.get("current_time"),
        "human_approval": raw.get("human_approval") is True,
        "disclosure_policy_verified": raw.get("disclosure_policy_verified") is True,
        "contract_errors": program_errors + offer_errors,
    }
