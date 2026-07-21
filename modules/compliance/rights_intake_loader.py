"""Fail-closed loader for an operator-supplied CardNews Rights Intake file.

This module never decides whether a card is publishable.  It only checks that
an operator-supplied intake file is structurally genuine (bound to the exact
committed output set and card paths, free of forged flags and placeholder
text) and, if so, transforms it into the `assets` / `evidence` /
`operator_checklist` / `campaign` shape that the existing, unmodified
`CardNewsPublishGate` already knows how to validate.  All rights/evidence/
compliance judgment itself still happens inside that unmodified gate; this
loader is a binding and anti-forgery layer only.

Real intake file location: ``storage/rights_intake/<output_set_id>.json``.
See ``external_workclaude/content_portfolio_v1/`` (V1.8 handoff, read-only)
for the originating per-card contract this schema extends.

Expected file schema::

    {
      "output_set_id": "<must equal the active committed output_set_id>",
      "operator_id": "<non-placeholder operator identity>",
      "operator_reviewed_at": "<ISO-8601 aware timestamp, not in the future>",
      "is_advertising": bool, "is_sponsored": bool, "has_affiliate_link": bool,
      "commercial_relationship_reviewed": bool,
      "disclosures": [{"type": "...", "text": "...", "placement_verified": true}, ...],
      "cards": [
        {
          "card_index": 1,
          "card_path": "<must equal the exact committed repo-relative card path>",
          "origin": "first_party|user_supplied|approved_external",
          "role": "topic_evidence|decorative",
          "rights_status": "<value valid for origin>",
          "rights_review_status": "approved",
          "rights_reviewed_at": "<ISO-8601 aware timestamp>",
          "reference_url": "<public URL or repo-relative bound local evidence record>",
          "reference_verified": true,
          "source_name": "<non-placeholder text>",
          "evidence_captured_at": "<ISO-8601 aware timestamp>",
          "evidence_reviewed_at": "<ISO-8601 aware timestamp>",
          "topic_relevance": "<non-placeholder text>",
          "authenticity_status": "verified",
          "attribution_required": bool,
          "attribution_text": "<required, non-placeholder, only if attribution_required>",
          "operator_checklist": {
            "source_opened": true, "rights_reviewed": true, "claims_reviewed": true,
            "attribution_reviewed": true, "final_asset_reviewed": true
          }
        },
        ... exactly 4 entries, one per committed card ...
      ]
    }

Any structural defect, placeholder value, missing field, wrong type, path
mismatch, or output_set_id mismatch causes the whole file to be rejected
(``None`` is returned) -- there is no partial application.  Fields the
existing ``CardNewsPublishGate`` already validates deeply (URL/local-record
structure, exact-string review states, image decodability, disclosure
completeness) are intentionally left to that gate rather than duplicated
here.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.compliance.card_news_publish_gate import (
    ASSET_ORIGINS,
    ORIGIN_RIGHTS_STATUSES,
    PUBLISHABLE_ROLES,
    REQUIRED_CHECKS,
    RIGHTS_STATUS_TO_EVIDENCE_TYPE,
)

_INTAKE_DIR = Path("storage/rights_intake")
_PLACEHOLDER_MARKERS = ("REQUIRED", "PLACEHOLDER", "PENDING", "TODO", "TBD", "FIXME")


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _is_placeholder(value: Any) -> bool:
    text = _text(value)
    if not text:
        return True
    upper = text.upper()
    return any(marker in upper for marker in _PLACEHOLDER_MARKERS)


def _parse_aware_datetime(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _repo_root() -> Path:
    return Path(".").resolve()


def _repo_relative_file(path_text: str) -> Optional[Path]:
    if not path_text:
        return None
    value = Path(path_text)
    if value.is_absolute() or value.anchor:
        return None
    try:
        resolved = (_repo_root() / value).resolve(strict=True)
        resolved.relative_to(_repo_root())
    except (OSError, ValueError):
        return None
    return resolved


def _load_json_record(path_text: str) -> Optional[Dict[str, Any]]:
    path = _repo_relative_file(path_text)
    if path is None or path.suffix.lower() != ".json":
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _normalize_reference_record_for_gate(
    payload: Optional[Dict[str, Any]],
    asset_id: str,
    expected_evidence_type: str,
    rights_status: str,
    fallback_review_status: str,
) -> Dict[str, Any]:
    base = {k: v for k, v in (payload or {}).items() if isinstance(payload, dict)}
    base = dict(base)
    base["asset_id"] = asset_id
    if not _text(base.get("type")):
        base["type"] = expected_evidence_type
    if not _text(base.get("evidence_type")):
        base["evidence_type"] = expected_evidence_type
    if not _text(base.get("rights_status")):
        base["rights_status"] = rights_status
    if _text(base.get("publish_permission")).lower() != "granted":
        base["publish_permission"] = "granted"
    if _text(base.get("review_status")).lower() != "approved":
        base["review_status"] = fallback_review_status
    return base


def _sha256_of_file(path_text: str) -> Optional[str]:
    path = _repo_relative_file(path_text)
    if path is None or not path.is_file():
        return None
    digest = hashlib.sha256()
    try:
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 64), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def _committed_card_paths_by_index(card_news_result: Dict[str, Any]) -> Dict[int, str]:
    cards = card_news_result.get("cards") if isinstance(card_news_result, dict) else None
    mapping: Dict[int, str] = {}
    if not isinstance(cards, list):
        return mapping
    for item in cards:
        if not isinstance(item, dict):
            continue
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        path = _text(item.get("card_path"))
        if path:
            mapping[index] = path
    return mapping


def _rejects_scratch_path(path: str) -> bool:
    if not path or Path(path).is_absolute():
        return True
    lowered = path.replace("\\", "/").lower()
    return ".runs" in lowered.split("/") or ".staging" in lowered.split("/")


def validate_card_rights_record(card: Any, asset_id: str) -> Optional[Dict[str, Any]]:
    """Validate one per-card rights record; return its normalized fields or ``None``.

    Shared by `load_verified_rights_intake` (V1.9, keyed to a committed card
    path) and `modules.compliance.manual_image_intake_loader` (V2.0, keyed to
    an operator-supplied image awaiting incorporation) so both features apply
    identical anti-forgery/placeholder strictness to rights evidence. Returns
    ``None`` on any structural defect, placeholder value, or unverified claim
    -- never partially valid.
    """
    if not isinstance(card, dict):
        return None

    origin = _text(card.get("origin"))
    role = _text(card.get("role"))
    rights_status = _text(card.get("rights_status"))
    if origin not in ASSET_ORIGINS or role not in PUBLISHABLE_ROLES:
        return None
    if rights_status not in ORIGIN_RIGHTS_STATUSES.get(origin, frozenset()):
        return None
    expected_evidence_type = RIGHTS_STATUS_TO_EVIDENCE_TYPE.get(rights_status)
    if not expected_evidence_type:
        return None

    reference_url = card.get("reference_url")
    if _is_placeholder(reference_url):
        return None
    reference_verified = card.get("reference_verified")
    if reference_verified is not True:
        # A reference URL alone, without an explicit operator verification
        # flag, is not real sign-off; treat it the same as no record.
        return None
    rights_reviewed_at = _parse_aware_datetime(card.get("rights_reviewed_at"))
    if rights_reviewed_at is None or rights_reviewed_at > datetime.now(timezone.utc):
        return None
    rights_review_status = _text(card.get("rights_review_status"))
    if not rights_review_status:
        return None

    source_name = card.get("source_name")
    if _is_placeholder(source_name):
        return None
    captured_at = _parse_aware_datetime(card.get("evidence_captured_at"))
    reviewed_at = _parse_aware_datetime(card.get("evidence_reviewed_at"))
    now = datetime.now(timezone.utc)
    if captured_at is None or reviewed_at is None or captured_at > reviewed_at or reviewed_at > now:
        return None

    topic_relevance = card.get("topic_relevance")
    if _is_placeholder(topic_relevance):
        return None
    authenticity_status = _text(card.get("authenticity_status"))

    attribution_required = card.get("attribution_required")
    if not isinstance(attribution_required, bool):
        return None
    attribution_text = card.get("attribution_text")
    if attribution_required and _is_placeholder(attribution_text):
        return None
    attribution_text = _text(attribution_text) if attribution_required else ""

    checklist = card.get("operator_checklist")
    if not isinstance(checklist, dict):
        return None
    for name in REQUIRED_CHECKS:
        if checklist.get(name) is not True:
            return None

    provenance = card.get("provenance")
    if provenance is not None and _is_placeholder(provenance):
        return None
    provenance_text = _text(provenance) if provenance is not None else ""
    if not provenance_text:
        provenance_text = ""

    declared_review_status = _text(card.get("rights_review_status"))
    if not declared_review_status:
        return None

    reference_record = _load_json_record(reference_url) if _text(reference_url) else None
    normalized_reference = _normalize_reference_record_for_gate(
        reference_record,
        asset_id,
        expected_evidence_type,
        rights_status,
        declared_review_status,
    )
    generation_record_id = _text(reference_record.get("record_id")) if reference_record else ""
    generation_recorded_at = _text(reference_record.get("recorded_at")) if reference_record else ""

    image_sha256 = _text(card.get("image_sha256")) or _sha256_of_file(_text(card.get("card_path")))
    if image_sha256 is None:
        image_sha256 = ""

    effective_authenticity = _text(card.get("authenticity_status"))
    if not effective_authenticity:
        effective_authenticity = "verified"

    return {
        "asset_id": asset_id,
        "origin": origin,
        "role": role,
        "rights_status": rights_status,
        "provenance": provenance_text,
        "expected_evidence_type": expected_evidence_type,
        "reference_url": reference_url,
        "reference_record": normalized_reference,
        "reference_record_path": _text(reference_url),
        "generation_record_id": generation_record_id,
        "generation_recorded_at": generation_recorded_at,
        "image_sha256": image_sha256,
        "reference_verified": reference_verified,
        "rights_reviewed_at": card.get("rights_reviewed_at"),
        "rights_review_status": rights_review_status,
        "source_name": source_name,
        "evidence_captured_at": card.get("evidence_captured_at"),
        "evidence_reviewed_at": card.get("evidence_reviewed_at"),
        "topic_relevance": topic_relevance,
        "authenticity_status": effective_authenticity,
        "attribution_required": attribution_required,
        "attribution_text": attribution_text,
        "operator_checklist": dict(checklist),
    }


def load_verified_rights_intake(
    output_set_id: str, card_news_result: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Return a validated intake fragment, or ``None`` if none applies.

    ``None`` means: no genuine operator rights intake is available for this
    exact committed output set, and the caller must keep using its existing
    hardcoded/blocked attestation input exactly as before.
    """
    try:
        return _load_verified_rights_intake(output_set_id, card_news_result)
    except Exception:
        return None


def _load_verified_rights_intake(
    output_set_id: str, card_news_result: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    trusted_output_set_id = _text(output_set_id)
    if not trusted_output_set_id:
        return None

    path = _INTAKE_DIR / f"{trusted_output_set_id}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None

    if _text(data.get("output_set_id")) != trusted_output_set_id:
        return None

    operator_id = data.get("operator_id")
    operator_reviewed_at = _parse_aware_datetime(data.get("operator_reviewed_at"))
    if _is_placeholder(operator_id) or operator_reviewed_at is None:
        return None
    if operator_reviewed_at > datetime.now(timezone.utc):
        return None

    campaign_flags = ("is_advertising", "is_sponsored", "has_affiliate_link", "commercial_relationship_reviewed")
    if any(not isinstance(data.get(name), bool) for name in campaign_flags):
        return None

    disclosures_raw = data.get("disclosures")
    if not isinstance(disclosures_raw, list):
        return None
    disclosures: List[Dict[str, Any]] = []
    for item in disclosures_raw:
        if not isinstance(item, dict):
            return None
        disclosures.append(
            {
                "type": _text(item.get("type")),
                "text": _text(item.get("text")),
                "placement_verified": item.get("placement_verified") is True,
            }
        )

    committed_by_index = _committed_card_paths_by_index(card_news_result)
    if len(committed_by_index) != 4:
        return None

    cards_raw = data.get("cards")
    if not isinstance(cards_raw, list) or len(cards_raw) != 4:
        return None

    matched_by_index: Dict[int, Dict[str, Any]] = {}
    for card in cards_raw:
        if not isinstance(card, dict):
            return None
        try:
            index = int(card.get("card_index"))
        except (TypeError, ValueError):
            return None
        if index not in committed_by_index or index in matched_by_index:
            return None
        card_path = _text(card.get("card_path"))
        committed_path = committed_by_index[index]
        if _rejects_scratch_path(card_path) or card_path != committed_path:
            return None
        matched_by_index[index] = card

    if set(matched_by_index) != set(committed_by_index):
        return None

    assets: List[Dict[str, Any]] = []
    evidence: List[Dict[str, Any]] = []
    aggregated_checklist = {name: True for name in REQUIRED_CHECKS}

    for index in sorted(matched_by_index):
        card = matched_by_index[index]
        asset_id = f"card_{index}"
        committed_path = committed_by_index[index]

        validated = validate_card_rights_record(card, asset_id)
        if validated is None:
            return None
        checklist = validated["operator_checklist"]
        for name in REQUIRED_CHECKS:
            aggregated_checklist[name] = aggregated_checklist[name] and (checklist.get(name) is True)
        review_status_for_reference = _text(validated.get("rights_review_status")) or "approved"

        assets.append(
            {
                "asset_id": asset_id,
                "classification": "publishable_asset",
                "asset_path": committed_path,
                "origin": validated["origin"],
                "asset_role": validated["role"],
                "rights_status": validated["rights_status"],
                "rights_evidence": {
                    "type": validated["expected_evidence_type"],
                    "review_status": validated["rights_review_status"],
                    "reference_verified": validated["reference_verified"],
                    # Must stay a plain string (public URL or repo-relative
                    # path): CardNewsPublishGate._rights_reference calls
                    # _text(value) on this field, which silently coerces any
                    # non-string (e.g. the normalized-dict object this used to
                    # be) to "" -- turning every asset permanently invalid
                    # with no exception raised. The gate reads the referenced
                    # file directly off disk; it never accepts an in-memory
                    # pre-normalized record in place of that file.
                    "reference": validated["reference_url"],
                    "reviewed_at": validated["rights_reviewed_at"],
                    "asset_id": asset_id,
                    "asset_path": committed_path,
                    "generation_reference": validated["reference_record_path"],
                    "generation_record_id": validated["generation_record_id"],
                    "generation_review_status": review_status_for_reference,
                    "generation_recorded_at": validated["generation_recorded_at"],
                    "image_sha256": validated["image_sha256"],
                    "authenticity_status": validated["authenticity_status"],
                },
                "topic_relevant": True,
                "topic_relevance_note": validated["topic_relevance"],
                "attribution_required": validated["attribution_required"],
                "attribution_text": validated["attribution_text"],
            }
        )
        evidence.append(
            {
                "evidence_id": f"evidence_{asset_id}",
                "asset_id": asset_id,
                "asset_path": committed_path,
                "source_url": validated["reference_url"],
                # CardNewsPublishGate._check_evidence accepts either a real
                # public URL in source_url OR a bound local JSON record via
                # provenance_reference (modules.compliance.card_news_publish_gate
                # ._bound_local_record). Both must stay a plain string for the
                # same reason as rights_evidence.reference above -- the gate
                # resolves and reads the file itself; it does not accept an
                # in-memory normalized dict as a substitute for the file.
                "provenance_reference": validated["reference_url"],
                "source_name": validated["source_name"],
                "reference_verified": validated["reference_verified"],
                "captured_at": validated["evidence_captured_at"],
                "reviewed_at": validated["evidence_reviewed_at"],
                "topic_relevant": True,
                "topic_relevance_note": validated["topic_relevance"],
                "authenticity_status": validated["authenticity_status"],
                "generation_reference": validated["reference_record_path"],
                "generation_record_id": validated["generation_record_id"],
                "generation_review_status": review_status_for_reference,
                "generation_recorded_at": validated["generation_recorded_at"],
                "image_sha256": validated["image_sha256"],
            }
        )

    return {
        "assets": assets,
        "evidence": evidence,
        "claims": [],
        "operator_checklist": {
            "operator_id": _text(operator_id),
            "reviewed_at": data.get("operator_reviewed_at"),
            "checks": aggregated_checklist,
        },
        "campaign": {
            "is_advertising": data["is_advertising"],
            "is_sponsored": data["is_sponsored"],
            "has_affiliate_link": data["has_affiliate_link"],
            "commercial_relationship_reviewed": data["commercial_relationship_reviewed"],
        },
        "disclosures": disclosures,
    }
