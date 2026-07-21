"""Commerce Phase 2A — SmartStore Adapter (Dry Run Only).

Design basis: `docs/RESEARCH/COMMERCE/SMARTSTORE_PRODUCT_CONTRACT.md`,
`docs/RESEARCH/COMMERCE/PLATFORM_API_EVIDENCE_MATRIX.md` §1.

Naver-specific facts baked into this adapter's checks (all traced to a
research doc, none invented):

- CONFIRMED (official channel): Naver has NO dedicated price/stock update
  endpoint -- the general product-modify endpoint requires a FULL payload
  resubmission, and any field omitted from that resubmission is treated as a
  deletion, not "leave unchanged." This is architecturally different from
  Coupang's item-level split and is called out explicitly in `dry_run()`'s
  result so a future Phase 2B implementer cannot miss it.
- CONFIRMED (official channel): the product-notice-information API requires a
  MAJOR (top-level, "대") category id, not the LEAF category id used for
  product registration itself -- two different category ids for one product.
"""

from __future__ import annotations

from typing import Any, Dict

from modules.commerce.marketplace_base import MarketplaceAdapterBase
from modules.commerce.schema_validator import ValidationResult


class SmartStoreAdapter(MarketplaceAdapterBase):
    @property
    def platform_name(self) -> str:
        return "smartstore"

    def dry_run(self, commerce_result: Dict[str, Any]) -> Dict[str, Any]:
        result = super().dry_run(commerce_result)
        result["platform_notes"] = [
            (
                "CONFIRMED (official channel): SmartStore has no dedicated price/stock "
                "endpoint. Any real modification call must resubmit the ENTIRE current "
                "product payload -- an omitted field is deleted, not preserved. A future "
                "adapter must always query current live state before building a "
                "modification request, never build one from Phase 1 output alone."
            ),
            (
                "CONFIRMED (official channel): notice-information lookups require the "
                "MAJOR (top-level) category id, not the leaf category id used for "
                "registration -- resolve both, do not assume one implies the other."
            ),
            "TODO(Phase 2B, CTO GATE): auth mechanism (OAuth2 + bcrypt-based signature) "
            "requires direct confirmation against apicenter.commerce.naver.com before any "
            "signing code is written.",
        ]
        return result

    def _platform_specific_checks(self, payload: Dict[str, Any], result: ValidationResult) -> ValidationResult:
        fields = payload.get("fields", {}) if isinstance(payload, dict) else {}
        category_entry = fields.get("category", {})
        notice_entry = fields.get("notice_information", {})

        if category_entry.get("status") == "ready" and notice_entry.get("status") == "ready":
            result.add_warning(
                "Both 'category' (leaf id) and 'notice_information' are present -- "
                "remember these resolve against DIFFERENT category-id levels on SmartStore "
                "(leaf vs. major). This adapter does not verify that distinction was honored; "
                "a human/Phase 2B category-resolution step must."
            )

        return result
