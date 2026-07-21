"""Fail-closed CardNews rights, provenance, claim and disclosure gate.

This module is deliberately offline and side-effect free.  It does not decide
whether publishing is lawful and it never publishes anything; it only reports
whether the supplied operator evidence is complete enough to proceed to the
existing human/manual-upload workflow.
"""

from __future__ import annotations

from datetime import datetime, timezone
import ipaddress
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from PIL import Image

from modules.common.external_storage import resolve_external_path
from modules.card_news.canvas_contract import is_allowed_card_slide_count


SCHEMA_VERSION = "card_news_compliance.v1"
RIGHTS_STATUS_TO_EVIDENCE_TYPE = {
    "owned": "ownership_record",
    "licensed": "license_url",
    "public_domain": "public_domain_record",
    "official_reuse_allowed": "official_reuse_policy",
    "user_supplied_with_permission": "written_permission",
    "permission_granted": "written_permission",
    "generated": "generation_record",
}
ASSET_ORIGINS = frozenset({"first_party", "user_supplied", "approved_external"})
ORIGIN_RIGHTS_STATUSES = {
    "first_party": frozenset({"owned", "generated"}),
    "user_supplied": frozenset({"user_supplied_with_permission", "permission_granted"}),
    "approved_external": frozenset({"licensed", "public_domain", "official_reuse_allowed", "permission_granted"}),
}
PUBLISHABLE_ROLES = frozenset({"topic_evidence", "decorative"})
DISCLOSURE_TYPES = frozenset({"advertising", "sponsorship", "affiliate"})
REQUIRED_CHECKS = (
    "source_opened",
    "rights_reviewed",
    "claims_reviewed",
    "attribution_reviewed",
    "final_asset_reviewed",
)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _aware_datetime(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _public_url(value: Any) -> bool:
    """Accept only credential-free HTTP(S) source URLs."""
    reference = _text(value)
    if not reference:
        return False
    parsed = urlparse(reference)
    hostname = (parsed.hostname or "").rstrip(".").lower()
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    return (
        parsed.scheme in {"http", "https"}
        and bool(hostname)
        and hostname != "localhost"
        and not hostname.endswith(".localhost")
        and not (address and (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_unspecified))
        and not parsed.username
        and not parsed.password
    )


def _existing_repo_file(value: Any) -> Optional[Path]:
    reference = _text(value)
    if not reference:
        return None
    try:
        candidate = Path(reference)
        resolved = (
            candidate if candidate.is_absolute() else _REPOSITORY_ROOT / candidate
        ).resolve(strict=True)
        allowed_roots = (
            _REPOSITORY_ROOT.resolve(),
            resolve_external_path("card_news").resolve(),
        )
        if not any(
            _is_relative_to(resolved, allowed_root) for allowed_root in allowed_roots
        ):
            return None
    except (OSError, ValueError):
        return None
    return resolved if resolved.is_file() else None


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _normalize_record(value: Any) -> Optional[Dict[str, Any]]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    resolved = _existing_repo_file(value)
    if resolved is None or resolved.suffix.lower() != ".json":
        return None
    try:
        record = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return record if isinstance(record, dict) else None


def _rights_reference(
    value: Any, asset_id: str, evidence_type: str, rights_status: str
) -> bool:
    if _public_url(value):
        return True
    record = _normalize_record(value)
    if record is None:
        return False
    if not isinstance(record, dict):
        return False
    record_type = _text(record.get("evidence_type") or record.get("type"))
    return (
        _text(record.get("asset_id")) == asset_id
        and _text(record.get("publish_permission")).lower() == "granted"
        and record_type == evidence_type
        and _text(record.get("rights_status")).lower() == rights_status
        and _text(record.get("review_status")).lower() == "approved"
    )


def _bound_local_record(value: Any, asset_id: str) -> bool:
    record = _normalize_record(value)
    if record is None:
        return False
    return (
        isinstance(record, dict)
        and _text(record.get("asset_id")) == asset_id
        and _text(record.get("review_status")).lower() == "approved"
    )


def _valid_image_file(value: Any) -> bool:
    path = _existing_repo_file(value)
    if path is None:
        return False
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
        return True
    except (OSError, ValueError):
        return False


def _repo_relative_path(value: Any) -> bool:
    reference = _text(value)
    if not reference:
        return False
    try:
        candidate = Path(reference)
        external_root = resolve_external_path("card_news").resolve()
        resolved = (
            candidate if candidate.is_absolute() else _REPOSITORY_ROOT / candidate
        ).resolve()
        # Keep the legacy safety contract for repository files: callers must
        # serialize those as repository-relative paths.  Absolute paths are
        # accepted only for the configured cross-drive CardNews store.
        allowed_roots = (
            (external_root,)
            if candidate.is_absolute()
            else (_REPOSITORY_ROOT.resolve(), external_root)
        )
    except (OSError, ValueError):
        return False
    return any(_is_relative_to(resolved, root) for root in allowed_roots)


class CardNewsPublishGate:
    """Validate an operator-supplied CardNews compliance intake package."""

    def check(self, intake: Any) -> Dict[str, Any]:
        try:
            return self._check(intake)
        except Exception:
            return self._result(None, [], [], [{"code": "compliance_internal_error", "message": "Compliance validation could not complete; publishing remains blocked."}], [], output_set_id=None)

    def _check(self, intake: Any) -> Dict[str, Any]:
        if not isinstance(intake, dict):
            return self._result(None, [], [], [{"code": "intake_invalid", "message": "Operator intake must be an object."}], [])

        package_id = _text(intake.get("package_id")) or None
        output_set_id = _text(intake.get("output_set_id")) or package_id
        blockers: List[Dict[str, Any]] = []
        if package_id is None:
            blockers.append({"code": "package_id_invalid", "message": "A non-empty explicit package_id is required for exact package binding."})
        if not _text(intake.get("output_set_id")):
            blockers.append({"code": "output_set_id_invalid", "message": "A non-empty explicit output_set_id is required for pre-publish attestation."})
        warnings: List[Dict[str, Any]] = []
        asset_results = self._check_assets(intake.get("assets"), package_id, output_set_id, blockers)
        evidence_results = self._check_evidence(intake.get("evidence"), asset_results, blockers)
        self._check_asset_evidence_links(asset_results, evidence_results, blockers)
        self._check_claims(intake.get("claims"), evidence_results, blockers)
        self._check_disclosures(intake.get("campaign"), intake.get("disclosures"), blockers)
        self._check_operator(intake.get("operator_checklist"), blockers)
        final_cards = self._check_final_cards(intake.get("final_cards"), output_set_id, blockers)
        quality = self._check_quality(intake.get("quality"), output_set_id, blockers)

        publishable_assets = [item for item in asset_results if item["classification"] == "publishable_asset"]
        if not publishable_assets:
            blockers.append({"code": "publishable_asset_missing", "message": "At least one validated publishable asset is required; technical fixtures do not count."})

        attribution = [
            {"asset_id": item["asset_id"], "text": item["attribution_text"]}
            for item in publishable_assets if item["attribution_required"]
        ]
        return self._result(package_id, asset_results, evidence_results, blockers, warnings, attribution, output_set_id, final_cards, quality)

    @staticmethod
    def _check_final_cards(raw: Any, output_set_id: Optional[str], blockers: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        cards = raw if isinstance(raw, list) else []
        normalized: List[Dict[str, str]] = []
        seen_paths = set()
        if not is_allowed_card_slide_count(len(cards)):
            blockers.append({"code": "final_cards_invalid", "message": "Explicit final_cards must use an allowed slide count."})
        for index, card in enumerate(cards):
            item = card if isinstance(card, dict) else {}
            path = _text(item.get("path"))
            card_output_set_id = _text(item.get("output_set_id"))
            if (not path or path in seen_paths or not _repo_relative_path(path) or not _valid_image_file(path) or
                    card_output_set_id != output_set_id):
                blockers.append({"code": "final_cards_invalid", "card_index": index, "message": "Each final card must be a unique decodable image inside repository or configured CardNews storage and bound to the exact output_set_id."})
            else:
                normalized.append({"path": path, "output_set_id": card_output_set_id})
            seen_paths.add(path)
        return normalized

    @staticmethod
    def _check_quality(raw: Any, output_set_id: Optional[str], blockers: List[Dict[str, Any]]) -> Dict[str, Any]:
        quality = raw if isinstance(raw, dict) else {}
        if quality.get("passed") is not True or _text(quality.get("output_set_id")) != output_set_id:
            blockers.append({"code": "quality_attestation_invalid", "message": "Quality must explicitly pass and bind to the exact output_set_id."})
            return {"passed": False, "output_set_id": _text(quality.get("output_set_id")) or None}
        return {"passed": True, "output_set_id": output_set_id}

    def _check_assets(self, raw: Any, package_id: Optional[str], output_set_id: Optional[str], blockers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not isinstance(raw, list):
            blockers.append({"code": "assets_invalid", "message": "assets must be a list."})
            return []
        results, seen = [], set()
        for index, asset in enumerate(raw):
            item = asset if isinstance(asset, dict) else {}
            asset_id = _text(item.get("asset_id")) or f"asset_{index}"
            classification = _text(item.get("classification"))
            valid = True
            if asset_id in seen:
                blockers.append({"code": "duplicate_asset_id", "asset_id": asset_id, "message": "Asset identifiers must be unique."}); valid = False
            seen.add(asset_id)
            if classification in {"technical_fixture", "technical_fixture_not_publish_approved"}:
                blockers.append({"code": "technical_fixture_not_publish_approved", "asset_id": asset_id, "message": "Technical fixtures are never publish-approved and cannot be included in a releasable asset package."})
                results.append({"asset_id": asset_id, "package_id": package_id, "output_set_id": output_set_id, "asset_path": _text(item.get("asset_path")), "origin": _text(item.get("origin")), "classification": "technical_fixture_not_publish_approved", "valid": False, "render_allowed": False, "rights_status": "", "rights_evidence_status": "blocked", "evidence_ids": [], "topic_relevant": False, "topic_status": "blocked", "attribution_status": "not_applicable", "attribution_required": False, "attribution_text": "", "manual_review_required": True})
                continue
            if classification != "publishable_asset":
                blockers.append({"code": "asset_classification_invalid", "asset_id": asset_id, "message": "Asset must be explicitly classified as publishable_asset or technical_fixture."}); valid = False
            origin = _text(item.get("origin"))
            role = _text(item.get("asset_role"))
            asset_path = _text(item.get("asset_path"))
            normalized_asset_path = asset_path.replace("\\", "/")
            rights_status = _text(item.get("rights_status"))
            rights = item.get("rights_evidence") if isinstance(item.get("rights_evidence"), dict) else {}
            if origin not in ASSET_ORIGINS or role not in PUBLISHABLE_ROLES:
                blockers.append({"code": "asset_provenance_invalid", "asset_id": asset_id, "message": "Publishable asset origin and role must use an approved explicit value."}); valid = False
            elif rights_status not in ORIGIN_RIGHTS_STATUSES[origin]:
                blockers.append({"code": "asset_origin_rights_mismatch", "asset_id": asset_id, "message": "Asset origin and rights_status must use the canonical approved combination."}); valid = False
            if origin == "first_party" and rights_status == "generated" and role != "decorative":
                blockers.append({"code": "generated_topic_evidence_forbidden", "asset_id": asset_id, "message": "First-party generated imagery may be decorative only and cannot serve as topic evidence."}); valid = False
            expected_type = RIGHTS_STATUS_TO_EVIDENCE_TYPE.get(rights_status)
            reviewed_at = _aware_datetime(rights.get("reviewed_at"))
            rights_ok = bool(expected_type) and not (not expected_type or _text(rights.get("type")) != expected_type or
                    _text(rights.get("review_status")) != "approved" or
                    rights.get("reference_verified") is not True or
                    not _rights_reference(rights.get("reference"), asset_id, expected_type or "", rights_status) or reviewed_at is None or
                    reviewed_at > datetime.now(timezone.utc) or
                    _text(rights.get("asset_id")) != asset_id)
            if not rights_ok:
                blockers.append({"code": "asset_rights_evidence_invalid", "asset_id": asset_id, "message": "Rights evidence is incomplete, inconsistent, ambiguous, or not approved."}); valid = False
            if _text(rights.get("asset_path")).replace("\\", "/") != normalized_asset_path:
                blockers.append({"code": "asset_file_binding_mismatch", "asset_id": asset_id, "message": "Rights evidence must bind to the exact repository-relative asset_path."}); valid = False
            if not _valid_image_file(asset_path):
                blockers.append({"code": "asset_file_invalid", "asset_id": asset_id, "message": "Publishable asset_path must resolve to an existing decodable image inside the repository."}); valid = False
            if item.get("topic_relevant") is not True or not _text(item.get("topic_relevance_note")):
                blockers.append({"code": "asset_topic_relevance_unverified", "asset_id": asset_id, "message": "Topic relevance must be explicitly confirmed and explained."}); valid = False
            attribution_value = item.get("attribution_required")
            attribution_required = attribution_value is True
            attribution_text = _text(item.get("attribution_text"))
            if not isinstance(attribution_value, bool):
                blockers.append({"code": "asset_attribution_ambiguous", "asset_id": asset_id, "message": "attribution_required must be an explicit boolean."}); valid = False
            if attribution_required and not attribution_text:
                blockers.append({"code": "asset_attribution_missing", "asset_id": asset_id, "message": "Required attribution text is missing."}); valid = False
            if origin == "approved_external" and (attribution_required is not True or not attribution_text):
                blockers.append({"code": "external_asset_attribution_required", "asset_id": asset_id, "message": "Approved external assets require explicit display attribution."}); valid = False
            results.append({
                "asset_id": asset_id,
                "package_id": package_id,
                "output_set_id": output_set_id,
                "asset_path": asset_path,
                "origin": origin,
                "classification": classification,
                "valid": valid,
                "render_allowed": valid,
                "rights_status": rights_status,
                "rights_evidence_status": "valid" if rights_ok else "blocked",
                "evidence_ids": [],
                "topic_relevant": item.get("topic_relevant") is True,
                "topic_status": "valid" if item.get("topic_relevant") is True and _text(item.get("topic_relevance_note")) else "blocked",
                "attribution_status": "valid" if isinstance(attribution_value, bool) and (not attribution_required or attribution_text) else "blocked",
                "attribution_required": attribution_required,
                "attribution_text": attribution_text,
                "manual_review_required": not valid,
            })
        return results

    def _check_evidence(self, raw: Any, assets: List[Dict[str, Any]], blockers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not isinstance(raw, list):
            blockers.append({"code": "evidence_invalid", "message": "evidence must be a list."})
            return []
        results, seen = [], set()
        publishable_ids = {item["asset_id"] for item in assets if item["classification"] == "publishable_asset"}
        now = datetime.now(timezone.utc)
        for index, evidence in enumerate(raw):
            item = evidence if isinstance(evidence, dict) else {}
            evidence_id = _text(item.get("evidence_id")) or f"evidence_{index}"
            asset_id = _text(item.get("asset_id"))
            valid = True
            if evidence_id in seen:
                blockers.append({"code": "duplicate_evidence_id", "evidence_id": evidence_id, "message": "Evidence identifiers must be unique."}); valid = False
            seen.add(evidence_id)
            captured = _aware_datetime(item.get("captured_at")); reviewed = _aware_datetime(item.get("reviewed_at"))
            asset_matches = asset_id in publishable_ids
            provenance_ok = (
                _public_url(item.get("source_url"))
                or _bound_local_record(item.get("provenance_reference"), asset_id)
            )
            matching_asset = next((asset for asset in assets if asset.get("asset_id") == asset_id), None)
            evidence_asset_path = _text(item.get("asset_path")).replace("\\", "/")
            asset_path_matches = bool(matching_asset) and evidence_asset_path == _text(matching_asset.get("asset_path")).replace("\\", "/")
            if not asset_matches:
                blockers.append({"code": "evidence_asset_mismatch", "evidence_id": evidence_id, "message": "Evidence must attest an existing publishable asset with the exact asset_id."}); valid = False
            if not asset_path_matches:
                blockers.append({"code": "asset_file_binding_mismatch", "asset_id": asset_id, "evidence_id": evidence_id, "message": "Evidence must bind to the exact repository-relative asset_path."}); valid = False
            if (not provenance_ok or item.get("reference_verified") is not True or not _text(item.get("source_name")) or
                    captured is None or reviewed is None or captured > reviewed or reviewed > now or
                    item.get("topic_relevant") is not True or not _text(item.get("topic_relevance_note")) or
                    item.get("authenticity_status") != "verified" or not asset_matches or not asset_path_matches):
                blockers.append({"code": "evidence_attestation_invalid", "evidence_id": evidence_id, "message": "Evidence provenance, relevance, timestamps, or authenticity attestation is incomplete or inconsistent."}); valid = False
            results.append({"evidence_id": evidence_id, "asset_id": asset_id, "valid": valid})
        return results

    @staticmethod
    def _check_asset_evidence_links(assets: List[Dict[str, Any]], evidence: List[Dict[str, Any]], blockers: List[Dict[str, Any]]) -> None:
        valid_asset_ids = {item["asset_id"] for item in evidence if item["valid"]}
        for asset in assets:
            if asset["classification"] != "publishable_asset":
                continue
            if asset["asset_id"] not in valid_asset_ids:
                asset["valid"] = False
                asset["render_allowed"] = False
                blockers.append({"code": "asset_evidence_link_invalid", "asset_id": asset["asset_id"], "message": "Publishable asset must link to valid evidence attested for that same asset."})
            asset["evidence_ids"] = [
                item["evidence_id"] for item in evidence
                if item.get("asset_id") == asset["asset_id"] and item.get("valid")
            ]
            asset["manual_review_required"] = not asset["valid"]

    @staticmethod
    def _check_claims(raw: Any, evidence: List[Dict[str, Any]], blockers: List[Dict[str, Any]]) -> None:
        if not isinstance(raw, list):
            blockers.append({"code": "claims_invalid", "message": "claims must be a list, including an empty list when there are no claims."}); return
        valid_ids = {item["evidence_id"] for item in evidence if item["valid"]}
        seen = set()
        for index, claim in enumerate(raw):
            item = claim if isinstance(claim, dict) else {}; claim_id = _text(item.get("claim_id")) or f"claim_{index}"
            refs = item.get("evidence_ids") if isinstance(item.get("evidence_ids"), list) else []
            refs = {_text(ref) for ref in refs if _text(ref)}
            if claim_id in seen or not _text(item.get("text")) or item.get("review_status") != "approved" or not refs or not refs.issubset(valid_ids):
                blockers.append({"code": "claim_evidence_invalid", "claim_id": claim_id, "message": "Claim text, approval, or linkage to valid evidence is incomplete or ambiguous."})
            seen.add(claim_id)

    @staticmethod
    def _check_disclosures(campaign: Any, raw: Any, blockers: List[Dict[str, Any]]) -> None:
        campaign = campaign if isinstance(campaign, dict) else {}
        required = set()
        relationship_fields = ("is_advertising", "is_sponsored", "has_affiliate_link", "commercial_relationship_reviewed")
        if any(not isinstance(campaign.get(name), bool) for name in relationship_fields):
            blockers.append({"code": "campaign_flags_ambiguous", "message": "Every commercial relationship flag must be an explicit boolean."})
        if campaign.get("is_advertising") is True: required.add("advertising")
        if campaign.get("is_sponsored") is True: required.add("sponsorship")
        if campaign.get("has_affiliate_link") is True: required.add("affiliate")
        disclosures = raw if isinstance(raw, list) else []
        supplied = {_text(item.get("type")) for item in disclosures if isinstance(item, dict) and _text(item.get("text")) and item.get("placement_verified") is True}
        if campaign.get("commercial_relationship_reviewed") is not True:
            blockers.append({"code": "commercial_relationship_unreviewed", "message": "Advertising, sponsorship, and affiliate relationship flags require explicit operator review."})
        for disclosure_type in sorted(required - supplied):
            blockers.append({"code": "disclosure_missing", "disclosure_type": disclosure_type, "message": "A required commercial disclosure is missing or its placement is unverified."})
        if any(value and value not in DISCLOSURE_TYPES for value in supplied):
            blockers.append({"code": "disclosure_type_invalid", "message": "Disclosure type is unsupported or ambiguous."})

    @staticmethod
    def _check_operator(raw: Any, blockers: List[Dict[str, Any]]) -> None:
        checklist = raw if isinstance(raw, dict) else {}
        operator_id = _text(checklist.get("operator_id")); reviewed = _aware_datetime(checklist.get("reviewed_at"))
        if not operator_id or reviewed is None or reviewed > datetime.now(timezone.utc):
            blockers.append({"code": "operator_attestation_invalid", "message": "Operator identity and a valid reviewed_at timestamp are required."})
        checks = checklist.get("checks") if isinstance(checklist.get("checks"), dict) else {}
        missing = [name for name in REQUIRED_CHECKS if checks.get(name) is not True]
        if missing:
            blockers.append({"code": "operator_checklist_incomplete", "fields": missing, "message": "Every required operator checklist item must be explicitly true."})

    @staticmethod
    def _result(package_id: Optional[str], assets: List[Dict[str, Any]], evidence: List[Dict[str, Any]], blockers: List[Dict[str, Any]], warnings: List[Dict[str, Any]], attribution: Optional[List[Dict[str, str]]] = None, output_set_id: Optional[str] = None, final_cards: Optional[List[Dict[str, str]]] = None, quality: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        publish_ready = not blockers
        evidence_by_asset = {
            item.get("asset_id"): "valid" if item.get("valid") else "blocked"
            for item in evidence if item.get("asset_id")
        }
        manual_reviews = [
            {"code": item["code"], "asset_id": item.get("asset_id"), "message": item["message"]}
            for item in blockers
        ]
        compliance_result = {
            "schema_version": SCHEMA_VERSION,
            "package_id": package_id,
            "output_set_id": output_set_id,
            "asset_ids": [item["asset_id"] for item in assets],
            "render_allowed_asset_ids": [item["asset_id"] for item in assets if item.get("render_allowed")],
            "status": "valid" if publish_ready else "blocked",
            "publish_ready": publish_ready,
            "actual_publish": False,
            "blocking_reasons": [dict(item) for item in blockers],
        }
        technical_fixture = any(item.get("classification") == "technical_fixture_not_publish_approved" for item in assets)
        attestation = {
            "schema_version": 1,
            "contract": "card_news_pre_publish_attestation_v1",
            "output_set_id": output_set_id,
            "package_id": package_id,
            "asset_ids": [item["asset_id"] for item in assets],
            "render_allowed_asset_ids": [item["asset_id"] for item in assets if item.get("render_allowed")],
            "cards": [dict(item) for item in (final_cards or [])],
            "rights": {"ready": publish_ready, "status": "pass" if publish_ready else "blocked"},
            "evidence": {"status": "applied" if publish_ready and evidence else "blocked", "items": [dict(item) for item in evidence]},
            "quality": dict(quality or {"passed": False, "output_set_id": None}),
            "release_guard": {"ready": publish_ready, "issue_codes": [item.get("code") for item in blockers]},
            "compliance_result": compliance_result,
            "technical_fixture_not_publish_approved": technical_fixture,
            "assets": [
                {
                    "asset_id": item["asset_id"],
                    "package_id": package_id,
                    "output_set_id": output_set_id,
                    "asset_path": item.get("asset_path", ""),
                    "origin": item.get("origin", ""),
                    "classification": item["classification"],
                    "rights_status": item.get("rights_status", "blocked"),
                    "rights_evidence_status": item.get("rights_evidence_status", "blocked"),
                    "evidence_status": evidence_by_asset.get(item["asset_id"], "blocked"),
                    "topic_status": item.get("topic_status", "blocked"),
                    "attribution_status": item.get("attribution_status", "blocked"),
                    "render_allowed": item.get("render_allowed") is True,
                }
                for item in assets
            ],
            "manual_reviews": manual_reviews,
            "publish_ready": publish_ready,
            "actual_publish": False,
            "blockers": [dict(item) for item in blockers],
        }
        return {
            "schema_version": SCHEMA_VERSION,
            "package_id": package_id,
            "output_set_id": output_set_id,
            "status": "valid" if not blockers else "blocked",
            "publish_ready": publish_ready,
            "actual_publish": False,
            "blocking_reasons": blockers,
            "warnings": warnings,
            "manual_reviews": manual_reviews,
            "asset_results": assets,
            "evidence_results": evidence,
            "render_allowed_asset_ids": [item["asset_id"] for item in assets if item.get("render_allowed")],
            "attribution": attribution or [],
            "operator_action": "consume_result" if not blockers else "correct_intake_and_recheck",
            "pre_publish_attestation": attestation,
        }
