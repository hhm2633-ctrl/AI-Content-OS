"""Adapter: V1.8 Rights Intake fixture/record shape -> V1.9 runtime input.

`external_workclaude/content_portfolio_v1/RIGHTS_INTAKE_CONTRACT_V1_8.json`
and `RIGHTS_INTAKE_ATTACK_FIXTURES_V1_8_1.json` (both read-only CTO/Spark
deliverables, never edited by this module) describe a flat per-card record
shape: `origin`, `role`, `rights_status`, `rights_evidence`, `source_url`,
`reference_verified`, `topic_relevance`, `authenticity_status`,
`operator_checklist`, `commercial_relationship_reviewed`, `output_set_id`,
`card_path`, `publish_ready`, `actual_publish`.

This module is the explicit bridge between that flat V1.8 record shape and
the richer V1.9 runtime schema consumed by
`modules.compliance.rights_intake_loader.load_verified_rights_intake`.  It
performs only structural/anti-forgery checks -- never business/semantic
compliance judgment (that remains the unmodified `CardNewsPublishGate`'s
job, reached only after `rights_intake_loader`'s deeper validation).  A
record that is structurally genuine but semantically incomplete (e.g. the
V1.8 contract's own placeholder-state records) still `passed=True` here --
it simply is not yet business-complete, which the deeper loader/gate will
separately and correctly keep blocked.

Blocker vocabulary and check semantics mirror
`RIGHTS_INTAKE_TEST_CONTRACT_V1_8_1.md` / `RIGHTS_INTAKE_ACCEPTANCE_MATRIX_V1_8_1.json`
exactly (read-only references, never modified): each record fails on the
first blocker code it matches, in this fixed priority order:

    RIGHTS_EVIDENCE_INVALID_TYPE
    PATH_FORBIDDEN_ABSOLUTE
    PATH_FORBIDDEN_RUNS_OR_STAGING
    OUTPUT_SET_ID_WHITESPACE_BLOCK
    OUTPUT_SET_ID_MISMATCH
    PUBLISH_FLAG_TRUE
    PUBLISH_FLAG_TYPE_INVALID
    FORGED_APPROVAL
    MISSING_REQUIRED_FIELDS
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

REQUIRED_FIELDS = (
    "origin",
    "role",
    "rights_status",
    "rights_evidence",
    "source_url",
    "reference_verified",
    "topic_relevance",
    "authenticity_status",
    "operator_checklist",
    "commercial_relationship_reviewed",
    "output_set_id",
    "card_path",
    "publish_ready",
    "actual_publish",
)
OPERATOR_CHECKLIST_KEYS = (
    "source_opened",
    "rights_reviewed",
    "claims_reviewed",
    "attribution_reviewed",
    "final_asset_reviewed",
)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _path_segments(value: str) -> List[str]:
    return [part.lower() for part in value.replace("\\", "/").split("/") if part]


def _is_scratch_segment_path(value: str) -> bool:
    return any(segment in (".runs", ".staging") for segment in _path_segments(value))


def _missing_required_fields(record: Dict[str, Any]) -> bool:
    for key in REQUIRED_FIELDS:
        if key not in record or record[key] is None:
            return True
    checklist = record.get("operator_checklist")
    if not isinstance(checklist, dict):
        return True
    for key in OPERATOR_CHECKLIST_KEYS:
        if key not in checklist or checklist[key] is None:
            return True
    return False


def _is_forged_approval(record: Dict[str, Any]) -> bool:
    checklist = record.get("operator_checklist")
    if not isinstance(checklist, dict):
        return False
    all_checks_true = all(checklist.get(key) is True for key in OPERATOR_CHECKLIST_KEYS)
    fully_declared_approved = (
        all_checks_true
        and record.get("reference_verified") is True
        and record.get("commercial_relationship_reviewed") is True
    )
    if not fully_declared_approved:
        return False
    rights_evidence = record.get("rights_evidence")
    proof_locator = rights_evidence.get("proof_locator") if isinstance(rights_evidence, dict) else None
    return not _text(proof_locator)


def adapt_v1_8_record(record: Dict[str, Any], trusted_output_set_id: str) -> Dict[str, Any]:
    """Classify one flat V1.8-style record; return a V1.9-shaped result.

    Returns ``{"passed": bool, "blocker_codes": [...], "normalized": dict|None}``.
    ``normalized`` is populated only when ``passed`` is True, and restates the
    record using the field names `modules.compliance.rights_intake_loader`
    expects (e.g. ``source_url`` -> ``reference_url``,
    ``rights_evidence.proof_locator`` -> ``rights_evidence_reference``).
    """
    if not isinstance(record, dict):
        return {"passed": False, "blocker_codes": ["MISSING_REQUIRED_FIELDS"], "normalized": None}

    rights_evidence = record.get("rights_evidence")
    if rights_evidence is not None and not isinstance(rights_evidence, dict):
        return {"passed": False, "blocker_codes": ["RIGHTS_EVIDENCE_INVALID_TYPE"], "normalized": None}

    card_path = record.get("card_path")
    card_path_text = card_path if isinstance(card_path, str) else ""
    if card_path_text and Path(card_path_text).is_absolute():
        return {"passed": False, "blocker_codes": ["PATH_FORBIDDEN_ABSOLUTE"], "normalized": None}
    if card_path_text and _is_scratch_segment_path(card_path_text):
        return {"passed": False, "blocker_codes": ["PATH_FORBIDDEN_RUNS_OR_STAGING"], "normalized": None}

    output_set_id = record.get("output_set_id")
    if isinstance(output_set_id, str):
        stripped = output_set_id.strip()
        if stripped == trusted_output_set_id and output_set_id != stripped:
            return {"passed": False, "blocker_codes": ["OUTPUT_SET_ID_WHITESPACE_BLOCK"], "normalized": None}
        if stripped != trusted_output_set_id:
            return {"passed": False, "blocker_codes": ["OUTPUT_SET_ID_MISMATCH"], "normalized": None}
    elif output_set_id is not None:
        return {"passed": False, "blocker_codes": ["OUTPUT_SET_ID_MISMATCH"], "normalized": None}

    for flag_name in ("publish_ready", "actual_publish"):
        if record.get(flag_name) is True:
            return {"passed": False, "blocker_codes": ["PUBLISH_FLAG_TRUE"], "normalized": None}
    for flag_name in ("publish_ready", "actual_publish"):
        value = record.get(flag_name)
        if value is not None and not isinstance(value, bool):
            return {"passed": False, "blocker_codes": ["PUBLISH_FLAG_TYPE_INVALID"], "normalized": None}

    if _is_forged_approval(record):
        return {"passed": False, "blocker_codes": ["FORGED_APPROVAL"], "normalized": None}

    if _missing_required_fields(record):
        return {"passed": False, "blocker_codes": ["MISSING_REQUIRED_FIELDS"], "normalized": None}

    checklist = record.get("operator_checklist") if isinstance(record.get("operator_checklist"), dict) else {}
    normalized = {
        "card_index": record.get("card_index"),
        "card_path": card_path_text,
        "origin": _text(record.get("origin")),
        "role": _text(record.get("role")),
        "rights_status": _text(record.get("rights_status")),
        "rights_evidence_reference": (
            _text(rights_evidence.get("proof_locator")) if isinstance(rights_evidence, dict) else ""
        ),
        "reference_url": _text(record.get("source_url")),
        "reference_verified": record.get("reference_verified") is True,
        "topic_relevance": record.get("topic_relevance"),
        "authenticity_status": _text(record.get("authenticity_status")),
        "commercial_relationship_reviewed": record.get("commercial_relationship_reviewed") is True,
        "operator_checklist": dict(checklist),
        "output_set_id": trusted_output_set_id,
    }
    return {"passed": True, "blocker_codes": [], "normalized": normalized}


def adapt_v1_8_fixture_file(
    fixtures: Dict[str, List[Dict[str, Any]]], trusted_output_set_id: str
) -> Dict[str, Dict[str, Any]]:
    """Run `adapt_v1_8_record` over every case in a V1.8/V1.8.1 fixture map.

    `fixtures` is the ``fixtures`` object from
    ``RIGHTS_INTAKE_ATTACK_FIXTURES_V1_8_1.json`` (or the V1.8 file): a dict
    of case_id -> list of one or more flat records.  Each case is reduced to
    a single classification by adapting its first record (every case in the
    V1.8.1 fixture file holds exactly one).
    """
    results: Dict[str, Dict[str, Any]] = {}
    for case_id, records in fixtures.items():
        record = records[0] if isinstance(records, list) and records else {}
        results[case_id] = adapt_v1_8_record(record, trusted_output_set_id)
    return results
