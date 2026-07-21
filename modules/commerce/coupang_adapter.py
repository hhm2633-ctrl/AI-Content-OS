"""Commerce Phase 2A — Coupang Adapter (Dry Run Only).

Design basis: `docs/RESEARCH/COMMERCE/COUPANG_PRODUCT_CONTRACT.md`,
`docs/RESEARCH/COMMERCE/PLATFORM_API_EVIDENCE_MATRIX.md` §2.

Coupang-specific facts baked into this adapter's checks (all traced to a
research doc, none invented):

- CONFIRMED: item-centric model -- `items[]`, not a flat product record; even
  a single-variant product needs one `items[]` entry.
- CONFIRMED: two-phase workflow (temp-save -> approval-request). This
  adapter's `dry_run()` always forces `workflow_control.requested = False`
  (already the default in `contract_loader.workflow_control_defaults()`) so a
  future real submission never auto-requests approval in the same call.
- CONFIRMED: once a product is "승인완료" (approved), price/stock changes MUST
  go through dedicated item-level endpoints, never the general modify
  endpoint -- this adapter flags that this payload shape is CREATE-time only.
- CONFIRMED (existence only): a live, moving "required purchase option"
  policy (effective 2026-02-02) can reject a submission outright if omitted.
"""

from __future__ import annotations

from typing import Any, Dict

from modules.commerce.marketplace_base import MarketplaceAdapterBase
from modules.commerce.schema_validator import ValidationResult


class CoupangAdapter(MarketplaceAdapterBase):
    @property
    def platform_name(self) -> str:
        return "coupang"

    def dry_run(self, commerce_result: Dict[str, Any]) -> Dict[str, Any]:
        result = super().dry_run(commerce_result)

        workflow_control = result.get("payload", {}).get("workflow_control", {})
        forced_requested_false = workflow_control.get("requested") is False

        result["platform_notes"] = [
            (
                "CONFIRMED: Coupang is item-centric (items[] array). Phase 1's flat "
                "'options' list must be transformed into one items[] entry per "
                "purchasable variant -- a real structural transform, not a rename. "
                "This builder does not perform that transform yet (TODO Phase 2B)."
            ),
            (
                f"CONFIRMED: two-phase workflow enforced -- workflow_control.requested "
                f"is forced to False ({forced_requested_false}) so temp-save never "
                f"auto-triggers an approval request."
            ),
            (
                "CONFIRMED: this payload shape is CREATE-time only. Once a product is "
                "approved, price/stock changes must use the dedicated item-level "
                "price/quantity endpoints -- never resubmit this payload for those fields."
            ),
            (
                "CONFIRMED (existence only): a live, category-dependent required-purchase-"
                "option policy (effective 2026-02-02) can reject registration outright if "
                "omitted -- re-verify against the Category Metadata Query API close to "
                "actual implementation, not from this static contract alone."
            ),
        ]
        return result

    def _platform_specific_checks(self, payload: Dict[str, Any], result: ValidationResult) -> ValidationResult:
        fields = payload.get("fields", {}) if isinstance(payload, dict) else {}
        workflow_control = payload.get("workflow_control", {}) if isinstance(payload, dict) else {}

        if workflow_control.get("requested") is not False:
            result.valid = False
            result.blocked_reasons.append({
                "code": "workflow_control_unsafe_default",
                "field": "workflow_control.requested",
                "severity": "blocking",
                "message": "workflow_control.requested must be False (temp-save only) for every Phase 2A payload.",
                "required_action": "Do not override workflow_control.requested in Phase 2A.",
            })

        fulfillment_entry = fields.get("fulfillment_model", {})
        if fulfillment_entry.get("status") in (None, "missing"):
            result.add_warning(
                "fulfillment_model (Marketplace vs. Rocket Growth) is undetermined -- "
                "Phase 1 has no concept of this today. A real submission must not assume "
                "standard Marketplace behavior without confirming this."
            )

        return result
