"""Immutable, fail-closed registry for owner-approved design references."""

from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


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
    }
)

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
