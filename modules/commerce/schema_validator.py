"""Commerce Phase 2A — Schema Validator.

Validates a payload dict (built by `payload_builder.py`) against a platform's
field contract (`contract_loader.py`). Pure, side-effect-free, no network I/O.

Fail Closed: any required field with a `None`/empty value, or any field that
carries a `pending_confirmation` marker (see `payload_builder.py`), is treated
as invalid -- never silently accepted because "the field is technically
present." This validator never becomes more permissive than the contract; it
only ever finds MORE problems than a naive presence check, never fewer.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from modules.commerce.contract_loader import load_contract


PENDING_MARKER = "pending_confirmation"

# Product notice information is category-dependent, but Phase 2A has no
# approved category-metadata lookup with which to prove that a notice template
# does not apply.  Treat absence as blocking instead of inferring exemption.
# This names only the canonical contract field; it does not assert or invent
# any exact marketplace payload sub-schema.
FAIL_CLOSED_CONDITIONAL_FIELDS = frozenset({"notice_information"})


class ValidationResult:
    """Plain result object -- deliberately not an exception. A blocked payload
    is expected, normal output, not an error condition (Fail Closed principle:
    blocking is the safe, correct outcome, not a failure)."""

    def __init__(self) -> None:
        self.valid: bool = True
        self.missing_fields: List[Dict[str, Any]] = []
        self.blocked_reasons: List[Dict[str, Any]] = []
        self.warnings: List[str] = []

    def add_missing(self, field: str, required: bool, reason_code: Optional[str], message: str) -> None:
        self.missing_fields.append({
            "field": field,
            "required": required,
            "reason": message,
            "required_action": f"Provide a Phase 1 verified fact for '{field}' before dry-run payload generation.",
        })

        if required:
            self.valid = False
            self.blocked_reasons.append({
                "code": reason_code or "missing_required_field",
                "field": field,
                "severity": "blocking",
                "message": message,
                "required_action": f"Resolve '{field}' via Phase 1's truth/source/freshness gates, then regenerate the payload.",
            })

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "missing_fields": self.missing_fields,
            "blocked_reasons": self.blocked_reasons,
            "warnings": self.warnings,
        }


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def validate_payload(platform: str, payload: Dict[str, Any]) -> ValidationResult:
    """Validate `payload` (as built by `payload_builder.build_payload()`)
    against `platform`'s contract.

    A field counts as present only when its value is non-empty AND is not the
    `pending_confirmation` sentinel `payload_builder` uses for fields whose
    exact platform key name is UNKNOWN per the research docs -- a
    pending-confirmation field must never silently pass validation just
    because *something* occupies its slot.
    """
    result = ValidationResult()

    try:
        contract = load_contract(platform)
    except Exception as error:
        result.valid = False
        result.blocked_reasons.append({
            "code": "contract_load_failed",
            "field": None,
            "severity": "blocking",
            "message": f"Could not load contract for platform '{platform}': {error}",
            "required_action": "Fix modules/commerce/contract_loader.py or config/commerce/marketplaces.json.",
        })
        return result

    fields = payload.get("fields", {}) if isinstance(payload, dict) else {}

    for field_name, spec in contract.items():
        classification = spec.get("classification", "optional")
        entry = fields.get(field_name) if isinstance(fields, dict) else None
        value = entry.get("value") if isinstance(entry, dict) else None
        is_pending = isinstance(entry, dict) and entry.get("status") == PENDING_MARKER

        if _is_empty(value) or is_pending:
            required = classification == "required"
            reason_code = spec.get("blocked_reason_code")

            if classification == "conditional" and not is_pending and _is_empty(value):
                # Conditional fields are only blocking when the payload itself
                # declared the condition applies, except legal/platform notice
                # information whose non-applicability cannot be established
                # without approved live category metadata.  That field fails
                # closed rather than silently becoming optional.
                condition_applies = (
                    field_name in FAIL_CLOSED_CONDITIONAL_FIELDS
                    or isinstance(entry, dict) and entry.get("condition_applies") is True
                )
                required = condition_applies

            reason_text = (
                f"'{field_name}' is pending platform-field confirmation (evidence tier: {spec.get('evidence_tier', 'UNKNOWN')})."
                if is_pending
                else f"'{field_name}' has no accepted Phase 1 fact (classification: {classification})."
            )

            result.add_missing(field_name, required=required, reason_code=reason_code, message=reason_text)

    if not fields:
        result.add_warning("Payload contains no fields at all -- likely an empty or malformed Phase 1 result.")

    return result
