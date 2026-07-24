"""Immutable, fail-closed registry for owner-approved design references."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from modules.design_learning.layout_blueprint_contract import (
    LayoutBlueprintValidationError,
    validate_layout_blueprint,
)
from modules.design_learning.reference_geometry_visual_gate import (
    SCHEMA_VERSION as VISUAL_GATE_SCHEMA_VERSION,
    evaluate_reference_geometry_draft,
)


SPECIMEN_REQUIRED_FIELDS = frozenset(
    {
        "reference_id",
        "source_claim_ids",
        "source_relative_path",
        "analysis_record_ids",
        "account_fit",
        "format_fit",
        "slide_role_fit",
        "topic_fit",
        "emotion_fit",
        "media_requirements",
        "blueprint_id",
        "approval_status",
        "owner_approval_receipt_id",
        "reference_only",
        "measured_performance_claimed",
        "geometry_visual_gate_receipt",
    }
)
REGISTRY_SCHEMA_VERSION = "owner_reference_v2_registry_v1"
REFERENCE_CANDIDATE_SCHEMA_VERSION = "owner_reference_v2_candidate_evidence_v1"
VISUAL_GATE_ADAPTER_SCHEMA_VERSION = "reference_geometry_visual_gate_adapter_v1"
INDEPENDENT_REVALIDATION_SCHEMA_VERSION = (
    "reference_geometry_independent_revalidation_v1"
)
SUPPORTED_SOURCE_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
)

REFERENCE_V2_INPUT_REQUIREMENTS = {
    "specimen": sorted(SPECIMEN_REQUIRED_FIELDS),
    "blueprint": [
        "blueprint_id",
        "blueprint_version",
        "canvas",
        "layout_family",
        "regions",
        "style_tokens",
        "fit_constraints",
        "geometry_hash",
        "provenance.reference_id",
    ],
    "production_approval": [
        "approval_status=owner_approved",
        "owner_approval_receipt_id",
        "geometry_visual_gate_receipt.status=pass",
        "reference_only=false",
    ],
}

_LIST_FIELDS = (
    "source_claim_ids",
    "analysis_record_ids",
    "account_fit",
    "format_fit",
    "slide_role_fit",
    "topic_fit",
    "emotion_fit",
)


class ReferenceSpecimenValidationError(ValueError):
    """Raised when a specimen is incomplete or unsafe for the registry."""


def _read_json_object(path: Path) -> Mapping[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, Mapping) else None


def _source_item(
    record: Mapping[str, Any],
    *,
    repository_root: Path,
    cache: dict[str, Mapping[str, Any] | None],
) -> Mapping[str, Any]:
    source_file = str(record.get("source_file") or "").strip()
    if not source_file:
        return {}
    if source_file not in cache:
        path = Path(source_file)
        if not path.is_absolute():
            path = repository_root / path
        cache[source_file] = _read_json_object(path)
    document = cache[source_file]
    if not isinstance(document, Mapping):
        return {}
    source_item_id = str(record.get("source_item_id") or "").strip()
    if source_item_id == "root":
        return document
    if source_item_id.startswith("item_"):
        try:
            index = int(source_item_id.split("_", 1)[1]) - 1
        except ValueError:
            return {}
        items = document.get("items")
        if isinstance(items, Sequence) and not isinstance(
            items, (str, bytes, bytearray)
        ):
            if 0 <= index < len(items) and isinstance(items[index], Mapping):
                return items[index]
    return {}


def _source_number(item: Mapping[str, Any]) -> int | None:
    value = item.get("source_no")
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None


def _resolve_source_reference(
    source_root: Path,
    source_number: int,
) -> tuple[str | None, str | None]:
    batch_number = ((source_number - 1) // 10) + 1
    offset = (source_number - 1) % 10
    batch_dir = source_root / f"batch_{batch_number:03d}"
    try:
        files = sorted(
            (
                path
                for path in batch_dir.iterdir()
                if path.is_file() and path.suffix.lower() in SUPPORTED_SOURCE_EXTENSIONS
            ),
            key=lambda path: path.name.casefold(),
        )
    except OSError:
        return None, f"batch_not_readable:{batch_number:03d}"
    if offset >= len(files):
        return None, f"source_number_not_mapped:{source_number}"
    try:
        relative = files[offset].relative_to(source_root.parent).as_posix()
    except ValueError:
        return None, f"source_path_outside_owner_root:{source_number}"
    return relative, None


def _is_visual_reference_record(record: Mapping[str, Any]) -> bool:
    formats = {
        str(value).strip().lower()
        for value in record.get("formats", [])
        if isinstance(value, str)
    }
    layers = {
        str(value).strip().lower()
        for value in record.get("learning_layers", [])
        if isinstance(value, str)
    }
    return "card_news" in formats and bool(
        layers.intersection(
            {"layout", "hook", "color", "typography", "image_media"}
        )
    )


def audit_existing_reference_v2_material(
    *,
    source_root: str | Path,
    taxonomy_payload: Mapping[str, Any],
    repository_root: str | Path,
) -> dict[str, Any]:
    """Build read-only candidate evidence without inventing V2 approval.

    Existing ``owner_confirmed`` learning records are retained as selection
    traces. Only an explicit ``OWNER_APPROVED`` source-item approval with a
    non-empty owner feedback event ID is recognized as legacy approval
    evidence, and even that remains reference-only until complete geometry is
    supplied and separately validated.
    """

    root = Path(source_root)
    repository = Path(repository_root)
    records = taxonomy_payload.get("records")
    records = records if isinstance(records, list) else []
    document_cache: dict[str, Mapping[str, Any] | None] = {}
    candidates: list[dict[str, Any]] = []
    selection_traces: list[dict[str, Any]] = []
    approval_traces: list[dict[str, Any]] = []
    mapping_errors: list[dict[str, Any]] = []

    for record in records:
        if not isinstance(record, Mapping):
            continue
        learning_id = str(record.get("learning_id") or "").strip()
        if not learning_id:
            continue
        if record.get("owner_confirmed") is True:
            selection_traces.append(
                {
                    "learning_id": learning_id,
                    "trace_type": "owner_confirmed_learning_signal",
                    "production_approval": False,
                }
            )
        if not _is_visual_reference_record(record):
            continue
        item = _source_item(
            record,
            repository_root=repository,
            cache=document_cache,
        )
        source_number = _source_number(item)
        if source_number is None:
            mapping_errors.append(
                {
                    "learning_id": learning_id,
                    "reason_code": "source_number_missing",
                }
            )
            continue
        source_relative_path, mapping_error = _resolve_source_reference(
            root,
            source_number,
        )
        if mapping_error or not source_relative_path:
            mapping_errors.append(
                {
                    "learning_id": learning_id,
                    "source_number": source_number,
                    "reason_code": mapping_error or "source_path_missing",
                }
            )
            continue

        approval = item.get("approval")
        approval = approval if isinstance(approval, Mapping) else {}
        legacy_status = str(approval.get("status") or "").strip().upper()
        legacy_event_id = str(
            approval.get("owner_feedback_event_id") or ""
        ).strip()
        exact_legacy_approval = (
            legacy_status == "OWNER_APPROVED" and bool(legacy_event_id)
        )
        if exact_legacy_approval:
            approval_traces.append(
                {
                    "learning_id": learning_id,
                    "source_relative_path": source_relative_path,
                    "owner_approval_receipt_id": legacy_event_id,
                    "trace_type": "explicit_legacy_owner_approval",
                    "requires_v2_geometry_before_selection": True,
                }
            )

        reference_digest = hashlib.sha256(
            f"{learning_id}|{source_relative_path}".encode("utf-8")
        ).hexdigest()[:20]
        accounts = [
            str(value).strip()
            for value in record.get("accounts", [])
            if isinstance(value, str) and value.strip()
        ]
        formats = [
            str(value).strip()
            for value in record.get("formats", [])
            if isinstance(value, str) and value.strip()
        ]
        candidates.append(
            {
                "candidate_schema_version": REFERENCE_CANDIDATE_SCHEMA_VERSION,
                "reference_id": f"owner-ref-{reference_digest}",
                "source_claim_ids": [learning_id],
                "source_relative_path": source_relative_path,
                "source_number": source_number,
                "analysis_record_ids": [learning_id],
                "account_fit_observed": accounts or ["shared"],
                "format_fit_observed": formats,
                "learning_layers_observed": copy.deepcopy(
                    record.get("learning_layers", [])
                ),
                "owner_confirmed_learning_signal": (
                    record.get("owner_confirmed") is True
                ),
                "approval_status": (
                    "owner_approved" if exact_legacy_approval else "candidate"
                ),
                "owner_approval_receipt_id": (
                    legacy_event_id if exact_legacy_approval else None
                ),
                "reference_only": True,
                "measured_performance_claimed": False,
                "suggested_blueprint_id": f"bp-owner-{reference_digest}",
                "known_analysis": {
                    key: copy.deepcopy(item.get(key))
                    for key in (
                        "observation",
                        "design_learning",
                        "project_learning",
                        "format_use",
                        "caution",
                    )
                    if item.get(key) is not None
                },
                "missing_required_inputs": [
                    "owner_validated_slide_role_fit",
                    "owner_validated_topic_fit",
                    "owner_validated_emotion_fit",
                    "media_requirements",
                    "complete_layout_blueprint_geometry",
                    "geometry_hash",
                ]
                + ([] if exact_legacy_approval else ["owner_approval_receipt_id"]),
                "production_selectable": False,
                "auto_approval_performed": False,
            }
        )

    exact_receipt_count = len(approval_traces)
    batch_dirs = (
        sorted(path for path in root.glob("batch_*") if path.is_dir())
        if root.is_dir()
        else []
    )
    image_count = 0
    for batch_dir in batch_dirs:
        try:
            image_count += sum(
                1
                for path in batch_dir.iterdir()
                if path.is_file()
                and path.suffix.lower() in SUPPORTED_SOURCE_EXTENSIONS
            )
        except OSError:
            continue
    blockers = [
        {
            "code": "complete_v2_geometry_blueprints_missing",
            "detail": "normalized regions, fit constraints, provenance, and geometry hashes are required",
        }
    ]
    if exact_receipt_count == 0:
        blockers.append(
            {
                "code": "owner_approval_receipts_missing",
                "detail": "owner_confirmed learning signals are not production approval receipts",
            }
        )
    if mapping_errors:
        blockers.append(
            {
                "code": "some_analysis_records_lack_source_mapping",
                "count": len(mapping_errors),
            }
        )
    return {
        "schema_version": REFERENCE_CANDIDATE_SCHEMA_VERSION,
        "status": "blocked_no_production_selectable_reference",
        "source_inventory": {
            "source_root": str(root),
            "batch_count": len(batch_dirs),
            "batch_image_count": image_count,
            "source_files_modified": False,
        },
        "analysis_inventory": {
            "record_count": len(records),
            "visual_reference_candidate_count": len(candidates),
            "owner_confirmed_learning_trace_count": len(selection_traces),
            "exact_legacy_owner_approval_count": exact_receipt_count,
        },
        "required_inputs": copy.deepcopy(REFERENCE_V2_INPUT_REQUIREMENTS),
        "candidate_evidence": candidates,
        "selection_traces": selection_traces,
        "approval_traces": approval_traces,
        "mapping_errors": mapping_errors,
        "blockers": blockers,
        "intermediate_artifact": {
            "status": "automatically_generatable" if candidates else "empty",
            "artifact_type": "reference_candidate_evidence",
            "production_registry": False,
        },
        "selectable_reference_ids": [],
        "auto_approval_performed": False,
        "external_write_performed": False,
    }


def extract_reference_draft_candidates(payload: Any) -> list[dict[str, Any]]:
    """Return detached, unapproved inputs eligible for geometry drafting.

    The input may be a complete audit result, a candidate-evidence object, or
    a bare candidate list. Approval and receipt fields are intentionally not
    promoted or normalized here.
    """

    if isinstance(payload, Mapping):
        raw_candidates = payload.get("candidate_evidence", [])
    else:
        raw_candidates = payload
    if not isinstance(raw_candidates, Sequence) or isinstance(
        raw_candidates, (str, bytes, bytearray)
    ):
        raise ReferenceSpecimenValidationError(
            "candidate evidence must be a list or contain candidate_evidence"
        )
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, value in enumerate(raw_candidates):
        if not isinstance(value, Mapping):
            raise ReferenceSpecimenValidationError(
                f"candidate_evidence[{index}] must be an object"
            )
        reference_id = _nonempty_string(
            value.get("reference_id"),
            f"candidate_evidence[{index}].reference_id",
        )
        source_relative_path = _nonempty_string(
            value.get("source_relative_path"),
            f"candidate_evidence[{index}].source_relative_path",
        )
        if reference_id in seen:
            raise ReferenceSpecimenValidationError(
                f"duplicate draft reference_id: {reference_id}"
            )
        seen.add(reference_id)
        candidate = copy.deepcopy(dict(value))
        candidate["reference_id"] = reference_id
        candidate["source_relative_path"] = source_relative_path
        candidate["draft_input_only"] = True
        candidate["production_selectable"] = False
        candidate["reference_only"] = True
        candidates.append(candidate)
    return candidates


def _nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReferenceSpecimenValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, field: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ReferenceSpecimenValidationError(f"{field} must be a list")
    result: list[str] = []
    for item in value:
        item_text = _nonempty_string(item, f"{field} item")
        if item_text not in result:
            result.append(item_text)
    if not result and not allow_empty:
        raise ReferenceSpecimenValidationError(f"{field} must not be empty")
    return result


def _reject_binary(value: Any, path: str = "specimen") -> None:
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise ReferenceSpecimenValidationError(
            f"{path} must not contain image bytes"
        )
    if isinstance(value, Mapping):
        for key, child in value.items():
            _reject_binary(child, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _reject_binary(child, f"{path}[{index}]")


def is_visual_gate_pass_receipt(
    receipt: Any,
    *,
    reference_id: str = "",
    blueprint_id: str = "",
    geometry_hash: str = "",
) -> bool:
    """Validate independent visual evidence without granting owner approval."""

    if not isinstance(receipt, Mapping):
        return False
    if receipt.get("schema_version") != VISUAL_GATE_SCHEMA_VERSION:
        return False
    if receipt.get("adapter_schema_version") != VISUAL_GATE_ADAPTER_SCHEMA_VERSION:
        return False
    if (
        receipt.get("independent_revalidation_schema_version")
        != INDEPENDENT_REVALIDATION_SCHEMA_VERSION
    ):
        return False
    if str(receipt.get("status") or "").strip() != "pass":
        return False
    if str(receipt.get("visual_status") or "").strip() != "visual_geometry_pass":
        return False
    for field in (
        "receipt_id",
        "source_receipt_path",
        "source_receipt_sha256",
        "reference_id",
        "blueprint_id",
        "geometry_hash",
        "gate_result_hash",
    ):
        if not str(receipt.get(field) or "").strip():
            return False
    if receipt.get("confidence_used_as_pass") is not False:
        return False
    if receipt.get("auto_owner_approval") is not False:
        return False
    if receipt.get("production_approval_granted") is not False:
        return False
    if reference_id and receipt.get("reference_id") != reference_id:
        return False
    if blueprint_id and receipt.get("blueprint_id") != blueprint_id:
        return False
    if geometry_hash and receipt.get("geometry_hash") != geometry_hash:
        return False
    return True


def adapt_reference_geometry_draft_for_visual_gate(
    draft: Mapping[str, Any],
    *,
    independent_receipt: Mapping[str, Any],
    independent_item: Mapping[str, Any],
    independent_receipt_path: str | Path,
) -> dict[str, Any]:
    """Map the nested draft schema through explicit, auditable paths."""

    blueprint = draft.get("blueprint_draft") if isinstance(draft, Mapping) else None
    blueprint = blueprint if isinstance(blueprint, Mapping) else {}
    provenance = blueprint.get("provenance")
    provenance = provenance if isinstance(provenance, Mapping) else {}
    regions = blueprint.get("regions")
    regions = (
        [copy.deepcopy(dict(item)) for item in regions if isinstance(item, Mapping)]
        if isinstance(regions, Sequence)
        and not isinstance(regions, (str, bytes, bytearray))
        else []
    )
    gate_regions: list[dict[str, Any]] = []
    recognized_text: list[str] = []
    for region in regions:
        text = str(
            region.get("recognized_text")
            or region.get("text")
            or ""
        ).strip()
        if text:
            recognized_text.append(text)
        gate_regions.append(
            {
                "region_id": region.get("region_id"),
                "role": region.get("role"),
                "text": text,
                "box": copy.deepcopy(
                    region.get("box_norm")
                    or region.get("box")
                    or region.get("bbox")
                ),
            }
        )
    reference_id = str(
        draft.get("reference_id")
        or provenance.get("reference_id")
        or ""
    ).strip()
    gate_input = {
        "geometry_contract_valid": draft.get("geometry_contract_valid") is True,
        "recognized_text": recognized_text,
        "crop_provenance": {
            "source_asset_id": reference_id,
            "crop_box": copy.deepcopy(
                provenance.get("crop_box_original_px")
            ),
            "method": str(provenance.get("crop_method") or "").strip(),
        },
        "canvas": copy.deepcopy(blueprint.get("canvas")),
        "regions": gate_regions,
    }
    gate_result = evaluate_reference_geometry_draft(gate_input)
    receipt_path = Path(independent_receipt_path)
    try:
        receipt_bytes = receipt_path.read_bytes()
    except OSError:
        receipt_bytes = b""
    receipt_sha256 = hashlib.sha256(receipt_bytes).hexdigest() if receipt_bytes else ""
    independent_valid = (
        independent_receipt.get("schema_version")
        == INDEPENDENT_REVALIDATION_SCHEMA_VERSION
        and independent_receipt.get("auto_approval_performed") is False
        and independent_item.get("reference_id") == reference_id
        and independent_item.get("visual_status") == "visual_geometry_pass"
        and independent_item.get("production_selectable") is False
    )
    integrated_pass = gate_result.get("status") == "pass" and independent_valid
    gate_result_hash = hashlib.sha256(
        json.dumps(
            gate_result,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    visual_receipt = None
    if integrated_pass:
        receipt_payload = {
            "reference_id": reference_id,
            "blueprint_id": blueprint.get("blueprint_id"),
            "geometry_hash": blueprint.get("geometry_hash"),
            "gate_result_hash": gate_result_hash,
            "source_receipt_sha256": receipt_sha256,
        }
        visual_receipt = {
            "schema_version": VISUAL_GATE_SCHEMA_VERSION,
            "adapter_schema_version": VISUAL_GATE_ADAPTER_SCHEMA_VERSION,
            "independent_revalidation_schema_version": (
                INDEPENDENT_REVALIDATION_SCHEMA_VERSION
            ),
            "status": "pass",
            "visual_status": "visual_geometry_pass",
            "receipt_id": "visual-gate-" + hashlib.sha256(
                json.dumps(
                    receipt_payload,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()[:24],
            "source_receipt_path": str(receipt_path),
            "source_receipt_sha256": receipt_sha256,
            **receipt_payload,
            "confidence_used_as_pass": False,
            "auto_owner_approval": False,
            "production_approval_granted": False,
        }
    if gate_result.get("status") != "pass":
        reason_code = "visual_geometry_gate_failed"
    elif not independent_valid:
        reason_code = "independent_visual_geometry_pass_missing"
    else:
        reason_code = "visual_geometry_candidate_pass"
    return {
        "schema_version": VISUAL_GATE_ADAPTER_SCHEMA_VERSION,
        "status": "pass" if integrated_pass else "rework_required",
        "reason_code": reason_code,
        "reference_id": reference_id,
        "blueprint_id": blueprint.get("blueprint_id"),
        "geometry_hash": blueprint.get("geometry_hash"),
        "gate_input": gate_input,
        "gate_result": gate_result,
        "geometry_visual_gate_receipt": visual_receipt,
        "adapter_receipt": {
            "source_schema_version": draft.get("schema_version"),
            "mapped_paths": {
                "canvas": "blueprint_draft.canvas",
                "regions": "blueprint_draft.regions",
                "recognized_text": (
                    "blueprint_draft.regions[*].recognized_text"
                ),
                "crop_box": (
                    "blueprint_draft.provenance.crop_box_original_px"
                ),
                "crop_method": "blueprint_draft.provenance.crop_method",
            },
            "silent_flattening_used": False,
            "confidence_used_as_pass": False,
        },
        "production_selectable": False,
        "auto_owner_approval": False,
    }


def validate_reference_specimen(specimen: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a detached normalized specimen record."""

    if not isinstance(specimen, Mapping):
        raise ReferenceSpecimenValidationError("specimen must be an object")
    missing = SPECIMEN_REQUIRED_FIELDS.difference(specimen)
    if missing:
        raise ReferenceSpecimenValidationError(
            f"specimen missing required fields: {', '.join(sorted(missing))}"
        )
    _reject_binary(specimen)
    normalized = copy.deepcopy(dict(specimen))
    for field in ("reference_id", "source_relative_path", "blueprint_id"):
        normalized[field] = _nonempty_string(normalized[field], field)
    for field in _LIST_FIELDS:
        normalized[field] = _string_list(normalized[field], field)
    if not isinstance(normalized["media_requirements"], Mapping):
        raise ReferenceSpecimenValidationError("media_requirements must be an object")
    normalized["media_requirements"] = copy.deepcopy(
        dict(normalized["media_requirements"])
    )
    normalized["approval_status"] = _nonempty_string(
        normalized["approval_status"], "approval_status"
    )
    receipt = normalized["owner_approval_receipt_id"]
    if receipt is not None:
        receipt = _nonempty_string(receipt, "owner_approval_receipt_id")
    if normalized["approval_status"] == "owner_approved" and not receipt:
        raise ReferenceSpecimenValidationError(
            "owner_approved specimen requires owner_approval_receipt_id"
        )
    normalized["owner_approval_receipt_id"] = receipt
    visual_receipt = normalized["geometry_visual_gate_receipt"]
    if not is_visual_gate_pass_receipt(
        visual_receipt,
        reference_id=normalized["reference_id"],
        blueprint_id=normalized["blueprint_id"],
    ):
        raise ReferenceSpecimenValidationError(
            "geometry_visual_gate_receipt must contain bound pass evidence"
        )
    normalized["geometry_visual_gate_receipt"] = copy.deepcopy(
        dict(visual_receipt)
    )
    if not isinstance(normalized["reference_only"], bool):
        raise ReferenceSpecimenValidationError("reference_only must be boolean")
    if normalized["measured_performance_claimed"] is not False:
        raise ReferenceSpecimenValidationError(
            "measured_performance_claimed must be false"
        )
    return normalized


def is_production_selectable(specimen: Mapping[str, Any]) -> bool:
    """Return true only for a valid owner-approved specimen with a receipt."""

    try:
        normalized = validate_reference_specimen(specimen)
    except ReferenceSpecimenValidationError:
        return False
    return (
        normalized["approval_status"] == "owner_approved"
        and bool(normalized["owner_approval_receipt_id"])
        and is_visual_gate_pass_receipt(
            normalized["geometry_visual_gate_receipt"],
            reference_id=normalized["reference_id"],
            blueprint_id=normalized["blueprint_id"],
        )
        and normalized["reference_only"] is False
    )


class ReferenceSpecimenRegistry:
    """In-memory registry that preserves registered records as immutable copies."""

    def __init__(self, specimens: Iterable[Mapping[str, Any]] = ()) -> None:
        self._specimens: dict[str, dict[str, Any]] = {}
        for specimen in specimens:
            self.register(specimen)

    def register(self, specimen: Mapping[str, Any]) -> dict[str, Any]:
        normalized = validate_reference_specimen(specimen)
        reference_id = normalized["reference_id"]
        if reference_id in self._specimens:
            raise ReferenceSpecimenValidationError(
                f"reference_id already registered: {reference_id}"
            )
        self._specimens[reference_id] = normalized
        return copy.deepcopy(normalized)

    def get(self, reference_id: str) -> dict[str, Any] | None:
        specimen = self._specimens.get(reference_id)
        return copy.deepcopy(specimen) if specimen is not None else None

    def all(self) -> list[dict[str, Any]]:
        return [
            copy.deepcopy(self._specimens[key])
            for key in sorted(self._specimens)
        ]

    def selectable(self) -> list[dict[str, Any]]:
        return [
            copy.deepcopy(self._specimens[key])
            for key in sorted(self._specimens)
            if is_production_selectable(self._specimens[key])
        ]

    def require_selectable(self, reference_id: str) -> dict[str, Any]:
        specimen = self._specimens.get(reference_id)
        if specimen is None:
            raise ReferenceSpecimenValidationError(
                f"unknown reference_id: {reference_id}"
            )
        if not is_production_selectable(specimen):
            raise ReferenceSpecimenValidationError(
                f"reference is not production-selectable: {reference_id}"
            )
        return copy.deepcopy(specimen)


def build_reference_v2_registry(
    specimens: Iterable[Mapping[str, Any]],
    blueprints: Mapping[str, Mapping[str, Any]] | Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate a detached registry without granting any new approval."""

    registry = ReferenceSpecimenRegistry(specimens)
    if isinstance(blueprints, Mapping):
        rows = [
            {**copy.deepcopy(dict(value)), "blueprint_id": key}
            if isinstance(value, Mapping) and not value.get("blueprint_id")
            else copy.deepcopy(dict(value))
            for key, value in blueprints.items()
            if isinstance(value, Mapping)
        ]
    else:
        rows = [
            copy.deepcopy(dict(value))
            for value in blueprints
            if isinstance(value, Mapping)
        ]

    normalized_blueprints: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, str]] = []
    for row in rows:
        blueprint_id = str(row.get("blueprint_id") or "").strip()
        if not blueprint_id:
            errors.append({"code": "blueprint_id_missing"})
            continue
        try:
            normalized_blueprints[blueprint_id] = validate_layout_blueprint(row)
        except LayoutBlueprintValidationError as exc:
            errors.append(
                {
                    "code": "blueprint_invalid",
                    "blueprint_id": blueprint_id,
                    "message": str(exc),
                }
            )

    selectable = registry.selectable()
    selectable_ids: list[str] = []
    for specimen in selectable:
        blueprint_id = specimen["blueprint_id"]
        blueprint = normalized_blueprints.get(blueprint_id)
        provenance = (
            blueprint.get("provenance")
            if isinstance(blueprint, Mapping)
            and isinstance(blueprint.get("provenance"), Mapping)
            else {}
        )
        if blueprint is None:
            errors.append(
                {
                    "code": "selectable_blueprint_missing",
                    "reference_id": specimen["reference_id"],
                    "blueprint_id": blueprint_id,
                }
            )
            continue
        if provenance.get("reference_id") != specimen["reference_id"]:
            errors.append(
                {
                    "code": "blueprint_reference_mismatch",
                    "reference_id": specimen["reference_id"],
                    "blueprint_id": blueprint_id,
                }
            )
            continue
        if not is_visual_gate_pass_receipt(
            specimen["geometry_visual_gate_receipt"],
            reference_id=specimen["reference_id"],
            blueprint_id=blueprint_id,
            geometry_hash=str(blueprint.get("geometry_hash") or ""),
        ):
            errors.append(
                {
                    "code": "visual_gate_geometry_binding_mismatch",
                    "reference_id": specimen["reference_id"],
                    "blueprint_id": blueprint_id,
                }
            )
            continue
        selectable_ids.append(specimen["reference_id"])

    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "status": "ready" if selectable_ids else "no_owner_approved_references",
        "specimens": registry.all(),
        "blueprints": normalized_blueprints,
        "selectable_reference_ids": sorted(selectable_ids),
        "errors": errors,
        "approval_policy": "owner_approved_with_receipt_only",
        "auto_approval_performed": False,
    }


def load_reference_v2_registry(path: str | Path) -> dict[str, Any]:
    """Load one registry path fail-closed and never mutate its data."""

    registry_path = Path(path)
    if not registry_path.is_file():
        return {
            "schema_version": REGISTRY_SCHEMA_VERSION,
            "status": "registry_not_found",
            "registry_path": str(registry_path),
            "specimens": [],
            "blueprints": {},
            "selectable_reference_ids": [],
            "errors": [],
            "auto_approval_performed": False,
        }
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ReferenceSpecimenValidationError("registry must be an object")
        result = build_reference_v2_registry(
            payload.get("specimens", []),
            payload.get("blueprints", {}),
        )
    except (
        OSError,
        json.JSONDecodeError,
        ReferenceSpecimenValidationError,
        TypeError,
        ValueError,
    ) as exc:
        return {
            "schema_version": REGISTRY_SCHEMA_VERSION,
            "status": "registry_invalid",
            "registry_path": str(registry_path),
            "specimens": [],
            "blueprints": {},
            "selectable_reference_ids": [],
            "errors": [{"code": "registry_invalid", "message": str(exc)}],
            "auto_approval_performed": False,
        }
    result["registry_path"] = str(registry_path)
    return result


__all__ = [
    "REFERENCE_CANDIDATE_SCHEMA_VERSION",
    "REFERENCE_V2_INPUT_REQUIREMENTS",
    "REGISTRY_SCHEMA_VERSION",
    "ReferenceSpecimenRegistry",
    "ReferenceSpecimenValidationError",
    "VISUAL_GATE_ADAPTER_SCHEMA_VERSION",
    "adapt_reference_geometry_draft_for_visual_gate",
    "audit_existing_reference_v2_material",
    "build_reference_v2_registry",
    "extract_reference_draft_candidates",
    "is_production_selectable",
    "is_visual_gate_pass_receipt",
    "load_reference_v2_registry",
    "validate_reference_specimen",
]
