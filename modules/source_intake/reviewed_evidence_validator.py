"""Validate caller-attested reviewed evidence with referential integrity.

This is an offline contract check, not identity authentication and not source
fetching. Every verified evidence id must resolve to an explicit human-reviewed
HTTPS evidence item that names the same claim.
"""

from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any, Mapping
from urllib.parse import urlsplit


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _aware_timestamp(value: Any) -> bool:
    raw = _text(value)
    if not raw:
        return False
    try:
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError, OverflowError):
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _nonempty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and item.strip() for item in value
    )


def _reviewed_https_url(value: Any) -> bool:
    raw = _text(value)
    if not raw:
        return False
    try:
        parsed = urlsplit(raw)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme.lower() == "https"
        and bool(hostname)
        and port in (None, 443)
        and parsed.username is None
        and parsed.password is None
    )


def is_verified_reviewed_evidence_bundle(value: Any) -> bool:
    """Return True only for a fully bound, caller-attested reviewed bundle."""
    if not isinstance(value, Mapping):
        return False
    if (
        value.get("status") != "verified"
        or value.get("verified") is not True
        or value.get("eligible") is not True
        or value.get("bundle_evidence_needs") != []
        or value.get("warnings") != []
    ):
        return False

    evidence_items = value.get("verified_evidence_items")
    if not isinstance(evidence_items, list) or not evidence_items:
        return False
    registry = {}
    for item in evidence_items:
        if not isinstance(item, Mapping):
            return False
        evidence_id = _text(item.get("evidence_id"))
        if not evidence_id or evidence_id in registry:
            return False
        if (
            item.get("verification_status") != "verified"
            or _text(item.get("reviewer_type")).lower() != "human"
            or not _aware_timestamp(item.get("reviewed_at"))
            or not _reviewed_https_url(item.get("source_url"))
            or not _nonempty_string_list(item.get("claim_ids"))
        ):
            return False
        registry[evidence_id] = set(item["claim_ids"])

    claims = value.get("claims")
    if not isinstance(claims, list) or not claims:
        return False
    seen_claim_ids = set()
    for claim in claims:
        if not isinstance(claim, Mapping):
            return False
        claim_id = _text(claim.get("claim_id"))
        verified_ids = claim.get("verified_evidence_ids")
        if (
            not claim_id
            or claim_id in seen_claim_ids
            or claim.get("status") != "verified"
            or claim.get("claim_alignment") is not True
            or claim.get("evidence_needs") != []
            or not _nonempty_string_list(verified_ids)
        ):
            return False
        seen_claim_ids.add(claim_id)
        for evidence_id in verified_ids:
            if evidence_id not in registry or claim_id not in registry[evidence_id]:
                return False
    return True


__all__ = ["is_verified_reviewed_evidence_bundle"]
