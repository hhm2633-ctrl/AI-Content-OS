"""Commerce Phase 2A — Payload Builder.

Builds a platform-shaped dry-run payload from an already-generated Commerce
Phase 1 `commerce_result` (`modules/commerce/commerce_module.py::CommerceModule.run()`
output). Pure, side-effect-free, no network I/O, no file writes -- returns a
plain dict.

Fail Closed (the single most important rule in this file): a value is included
in the payload if and only if it is present in Phase 1's already-gated
`platform_packages.<platform>` / `detail_page` output (the only two roots
CommerceModule's result dict actually exposes -- see `contract_loader.py`'s
module docstring for the confirmed field-by-field mapping, including the
several fields, e.g. category/price/stock/vendor_id, that Phase 1 validates
internally but never renders into its output at all today). This builder
never reads Phase 1's `raw` input, never re-derives a value from an unverified
source, and never invents a placeholder to satisfy a platform's "field must be
non-empty" expectation. When a field's exact platform key name is UNKNOWN per
the research docs (`docs/RESEARCH/COMMERCE/SMARTSTORE_PRODUCT_CONTRACT.md` /
`COUPANG_PRODUCT_CONTRACT.md`), the field is marked `pending_confirmation`
rather than guessed -- `schema_validator.py` treats that marker as not-present.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from modules.commerce.contract_loader import load_contract, workflow_control_defaults

PENDING_MARKER = "pending_confirmation"


def _resolve_path(commerce_result: Dict[str, Any], dotted_path: str, platform: str) -> Any:
    """Resolve a dotted path (e.g. 'platform_packages.{platform}.product_name')
    against `commerce_result`. Returns None on any missing segment -- never
    raises, since a missing Phase 1 field is an expected, common case."""
    path = dotted_path.replace("{platform}", platform)
    node: Any = commerce_result

    for segment in path.split("."):
        if isinstance(node, dict) and segment in node:
            node = node[segment]
        else:
            return None

    return node


def _build_field_entry(
    commerce_result: Dict[str, Any],
    platform: str,
    field_name: str,
    spec: Dict[str, Any],
) -> Dict[str, Any]:
    platform_field = spec.get("platform_field")
    phase1_sources = spec.get("phase1_sources")

    if phase1_sources:
        # Composite field (e.g. SmartStore brand_manufacturer = brand + manufacturer).
        resolved = {
            source.rsplit(".", 1)[-1]: _resolve_path(commerce_result, source, platform)
            for source in phase1_sources
        }
        value: Any = resolved if any(v not in (None, "", [], {}) for v in resolved.values()) else None
    else:
        phase1_source = spec.get("phase1_source")
        value = _resolve_path(commerce_result, phase1_source, platform) if phase1_source else None

    entry: Dict[str, Any] = {
        "value": value,
        "phase1_source": spec.get("phase1_source") or spec.get("phase1_sources"),
        "platform_field": platform_field,
        "classification": spec.get("classification"),
        "evidence_tier": spec.get("evidence_tier"),
    }

    if value not in (None, "", [], {}) and platform_field is None:
        # A real Phase 1 value exists, but the exact platform key name is
        # UNKNOWN per the research docs -- mark pending rather than emit a
        # guessed key name. This is a deliberate, visible gap, not a bug.
        entry["status"] = PENDING_MARKER
        entry["reason"] = (
            f"Phase 1 value is present, but the exact platform field name for "
            f"'{field_name}' is UNKNOWN per docs/RESEARCH/COMMERCE/ -- see contract_loader.py."
        )
    elif value not in (None, "", [], {}):
        entry["status"] = "ready"
    else:
        entry["status"] = "missing"

    condition = spec.get("condition")
    if condition:
        entry["condition"] = condition
        # Conditional fields are only "blocking" when Phase 1 actually
        # populated a related option/variant signal. This builder never
        # invents that signal -- it only marks the condition text so a human
        # reviewer (or schema_validator, for options specifically) can judge.
        if field_name in ("options", "required_purchase_options"):
            entry["condition_applies"] = bool(value)

    return entry


def build_payload(platform: str, commerce_result: Dict[str, Any]) -> Dict[str, Any]:
    """Build a dry-run payload for `platform` from a Phase 1 `commerce_result`.

    Returns a dict shaped:
        {
            "platform": ...,
            "built_at": ISO-8601 UTC,
            "phase1_status": commerce_result.status (for traceability),
            "phase1_request_id": commerce_result.request_id,
            "workflow_control": {...always-safe values, e.g. requested=False...},
            "fields": {field_name: {value, platform_field, status, ...}, ...},
        }

    Never raises on a malformed `commerce_result` -- returns a payload with all
    fields marked missing instead, since "no Phase 1 data" is itself a valid,
    expected input this builder must handle safely (Fail Closed, not Fail Open
    to an exception that could bypass the validator/approval gate downstream).
    """
    commerce_result = commerce_result if isinstance(commerce_result, dict) else {}
    contract = load_contract(platform)

    fields: Dict[str, Any] = {
        field_name: _build_field_entry(commerce_result, platform, field_name, spec)
        for field_name, spec in contract.items()
    }

    return {
        "platform": platform,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "phase1_status": commerce_result.get("status"),
        "phase1_request_id": commerce_result.get("request_id"),
        "phase1_generated_at": commerce_result.get("generated_at"),
        "workflow_control": workflow_control_defaults(platform),
        "fields": fields,
    }


def summarize_gaps(payload: Dict[str, Any]) -> Dict[str, List[str]]:
    """Convenience summary: which fields are ready / missing / pending
    confirmation. Used by `dry_run_executor.py` for a human-readable report
    without re-deriving anything the payload doesn't already carry."""
    fields = payload.get("fields", {}) if isinstance(payload, dict) else {}

    ready = [name for name, entry in fields.items() if entry.get("status") == "ready"]
    missing = [name for name, entry in fields.items() if entry.get("status") == "missing"]
    pending = [name for name, entry in fields.items() if entry.get("status") == PENDING_MARKER]

    return {"ready": ready, "missing": missing, "pending_confirmation": pending}
