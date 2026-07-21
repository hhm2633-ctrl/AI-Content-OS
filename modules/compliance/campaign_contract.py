"""Campaign Compliance Phase 1 -- input contract normalization.

Defensive dict-in/dict-out normalization for the two input shapes this checker
consumes: `CampaignRequirement` (a single condition an advertiser/sponsor sets)
and `ContentPackage` (the actual content being checked). Neither function ever
raises or mutates the caller's raw input -- every value is read via `.get()`
and copied into a brand-new dict/list, mirroring the defensive-parsing pattern
already used in `modules/content/content_output_normalizer.py` and
`modules/card_news/evidence_input_validator.py`.

This module performs no I/O, no network access, and no LLM calls.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

REQUIREMENT_TYPES = frozenset({
    "required_keyword",
    "prohibited_keyword",
    "disclosure_text",
    "image_count",
    "video_required",
    "map_required",
    "link_required",
    "hashtag",
    "brand_name",
    "product_name",
    "publishing_window",
    "numeric_claim",
    "manual_instruction",
})


def _clean_str(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _clean_str_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, (str, int, float))]


def _clean_number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


ALLOWED_VERIFICATION_MODES = frozenset({"automatic", "manual", "evidence_required"})


def normalize_requirement(raw: Any) -> Dict[str, Any]:
    """Return a canonical `CampaignRequirement` dict. Never raises.

    `required` defaults to `True` when not an explicit boolean -- fail-closed:
    an ambiguous/missing `required` flag is treated as "this condition must
    hold", not silently optional. `verification_mode` is normalized
    (stripped/lowercased) but NOT validated here -- an unrecognized value is a
    per-requirement contract defect the checker blocks explicitly (see
    `campaign_compliance_checker.py`), not something this normalizer should
    silently coerce or drop.
    """
    raw = raw if isinstance(raw, dict) else {}

    required_value = raw.get("required")
    required = required_value if isinstance(required_value, bool) else True

    return {
        "requirement_id": raw.get("requirement_id"),
        "requirement_type": _clean_str(raw.get("requirement_type")).strip().lower(),
        "description": _clean_str(raw.get("description")),
        "required": required,
        "expected_value": raw.get("expected_value"),
        "minimum_count": _clean_number(raw.get("minimum_count")),
        "maximum_count": _clean_number(raw.get("maximum_count")),
        "allowed_values": _clean_str_list(raw.get("allowed_values")),
        "prohibited_values": _clean_str_list(raw.get("prohibited_values")),
        "verification_mode": _clean_str(raw.get("verification_mode")).strip().lower(),
        "source_reference": raw.get("source_reference") if isinstance(raw.get("source_reference"), str) else None,
    }


def normalize_requirements(raw_list: Any) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Normalize a list of raw requirement dicts.

    A duplicate `requirement_id` is a **contract-level blocker**, not a
    silently-deduplicated warning (NO-GO fix: a caller could previously smuggle
    a second, conflicting requirement past review under an id already used by
    a stricter one). The second-and-later `requirement_id` list is returned as
    `contract_errors`; the caller must treat any non-empty `contract_errors`
    as "do not evaluate this campaign", not "proceed with best effort". A
    missing/blank `requirement_id` is assigned a stable positional id so every
    requirement remains addressable before duplication is checked.
    """
    if not isinstance(raw_list, list):
        return [], ["campaign requirements missing or not a list"]

    contract_errors: List[str] = []
    seen_ids = set()
    clean: List[Dict[str, Any]] = []

    for index, raw in enumerate(raw_list):
        item = normalize_requirement(raw)
        raw_id = raw.get("requirement_id") if isinstance(raw, dict) else None
        requirement_id = str(raw_id).strip() if isinstance(raw_id, str) and raw_id.strip() else f"unspecified_{index}"

        if requirement_id in seen_ids:
            contract_errors.append(f"duplicate requirement_id '{requirement_id}' at index {index}")
            continue

        seen_ids.add(requirement_id)
        item["requirement_id"] = requirement_id
        clean.append(item)

    return clean, contract_errors


def _normalize_evidence_reference(raw: Any) -> Dict[str, Any]:
    """Return a canonical, structured evidence-reference dict.

    NO-GO fix: a bare string used to be accepted directly as "evidence" by
    string-equality against `source_reference`. A bare string is still parsed
    here (as an `evidence_id` only) so it is never silently dropped, but every
    other required field (`source_url`/`locator`, `captured_at`,
    `verified_at`, `rights_status`) stays empty -- which makes such a shell
    entry structurally incomplete by construction, so `campaign_compliance_checker.py`'s
    completeness check can never treat an arbitrary string as sufficient
    evidence on its own.
    """
    if isinstance(raw, str):
        return {
            "evidence_id": raw.strip(),
            "source_url": None,
            "locator": None,
            "captured_at": None,
            "verified_at": None,
            "rights_status": "",
        }

    if isinstance(raw, dict):
        source_url = raw.get("source_url")
        locator = raw.get("locator")
        return {
            "evidence_id": _clean_str(raw.get("evidence_id")),
            "source_url": source_url if isinstance(source_url, str) and source_url.strip() else None,
            "locator": locator if isinstance(locator, str) and locator.strip() else None,
            "captured_at": raw.get("captured_at"),
            "verified_at": raw.get("verified_at"),
            "rights_status": _clean_str(raw.get("rights_status")).strip().lower(),
        }

    return {
        "evidence_id": "",
        "source_url": None,
        "locator": None,
        "captured_at": None,
        "verified_at": None,
        "rights_status": "",
    }


def _normalize_evidence_refs(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [_normalize_evidence_reference(item) for item in value]


def _normalize_rights_manifest(value: Any) -> Dict[str, Dict[str, Any]]:
    """Return `{manifest_id: {"rights_status": "..."}}`.

    An "upstream rights manifest" an asset can link to instead of carrying its
    own `rights_status` directly (NO-GO fix 11: an asset must have one or the
    other, never neither).
    """
    if not isinstance(value, dict):
        return {}

    manifest: Dict[str, Dict[str, Any]] = {}
    for key, entry in value.items():
        if isinstance(entry, dict):
            manifest[str(key)] = {"rights_status": _clean_str(entry.get("rights_status")).strip().lower()}
    return manifest


def normalize_content_package(raw: Any) -> Dict[str, Any]:
    """Return a canonical `ContentPackage` dict. Never raises.

    `links` accepts either plain URL strings or `{"url": "..."}` dicts.
    `assets` entries are shallow-copied dicts (never the caller's originals).
    `publishing_time` is preserved as-is (str/datetime) -- timezone parsing
    happens later, only where a requirement actually needs it. `evidence_refs`
    is a list of structured evidence-reference dicts (see
    `_normalize_evidence_reference`), not bare strings. `rights_manifest` is
    an additive, optional field: `{manifest_id: {"rights_status": ...}}` an
    asset may link to via `upstream_rights_manifest_id`.
    """
    raw = raw if isinstance(raw, dict) else {}

    assets_raw = raw.get("assets")
    assets: List[Dict[str, Any]] = []
    if isinstance(assets_raw, list):
        assets = [dict(asset) for asset in assets_raw if isinstance(asset, dict)]

    links_raw = raw.get("links")
    links: List[str] = []
    if isinstance(links_raw, list):
        for entry in links_raw:
            if isinstance(entry, str):
                links.append(entry)
            elif isinstance(entry, dict) and isinstance(entry.get("url"), str):
                links.append(entry["url"])

    return {
        "package_id": _clean_str(raw.get("package_id")),
        "channel": _clean_str(raw.get("channel")),
        "title": _clean_str(raw.get("title")),
        "body": _clean_str(raw.get("body")),
        "caption": _clean_str(raw.get("caption")),
        "hashtags": _clean_str_list(raw.get("hashtags")),
        "links": links,
        "assets": assets,
        "publishing_time": raw.get("publishing_time"),
        "evidence_refs": _normalize_evidence_refs(raw.get("evidence_refs")),
        "rights_status": _clean_str(raw.get("rights_status")),
        "rights_manifest": _normalize_rights_manifest(raw.get("rights_manifest")),
    }


def normalize_campaign_contract(raw: Any) -> Dict[str, Any]:
    """Return `{"campaign_id", "requirements", "contract_valid", "contract_errors"}`.

    Accepts either `{"campaign_id": ..., "requirements": [...]}` or a bare
    list of raw requirement dicts (campaign_id then stays `None`). Any other
    shape -- a missing `requirements` key on a dict, a non-list
    `requirements` value, or a root that is neither a dict nor a list (e.g.
    `123`) -- is a **contract-level error**: `contract_valid` is `False` and
    `contract_errors` explains why. A duplicate `requirement_id` (see
    `normalize_requirements`) is folded into the same `contract_errors` list.
    The caller must never evaluate requirements against content when
    `contract_valid` is `False` -- see
    `campaign_compliance_checker.py::CampaignComplianceChecker._check`.
    """
    contract_errors: List[str] = []

    if isinstance(raw, dict):
        campaign_id_raw = raw.get("campaign_id")
        if "requirements" not in raw:
            contract_errors.append("campaign dict is missing a 'requirements' field")
            requirements_raw: Any = []
        else:
            requirements_raw = raw.get("requirements")
            if not isinstance(requirements_raw, list):
                contract_errors.append("campaign.requirements must be a list")
                requirements_raw = []
    elif isinstance(raw, list):
        campaign_id_raw = None
        requirements_raw = raw
    else:
        campaign_id_raw = None
        requirements_raw = []
        contract_errors.append(
            "campaign must be a dict with a 'requirements' list, or a bare list of requirements"
        )

    campaign_id = str(campaign_id_raw).strip() if isinstance(campaign_id_raw, str) and campaign_id_raw.strip() else None
    requirements, requirement_errors = normalize_requirements(requirements_raw)
    contract_errors.extend(requirement_errors)

    return {
        "campaign_id": campaign_id,
        "requirements": requirements,
        "contract_valid": not contract_errors,
        "contract_errors": contract_errors,
    }
