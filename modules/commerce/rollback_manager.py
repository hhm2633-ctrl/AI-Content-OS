"""Commerce Phase 2A — Rollback Manager.

Defines the rollback/deactivation interface for a future real listing. In
Phase 2A there is nothing live to roll back (no real submission ever happens
this Sprint), so every method here is dry-run-only: it records what a
rollback *would* do and why, without making a network call.

Design basis:
- `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.14 (rollback should call
  each platform's own stop-sales/deactivation endpoint, never a hard delete).
- `docs/RESEARCH/COMMERCE/PLATFORM_API_EVIDENCE_MATRIX.md` §2.5: Coupang has a
  CONFIRMED item-level "판매중지" (stop-sales) capability. Naver's equivalent
  deactivation mechanism is UNKNOWN.
- `docs/RESEARCH/COMMERCE/SECURITY_COMPLIANCE_GATE.md` §10 Stage 3 rollback
  trigger: any policy rejection or price/stock/content mismatch must trigger
  immediate deactivation via the platform's confirmed capability, plus a
  mandatory incident write-up regardless of outcome.

TODO(Phase 2B/2C): implement the real Coupang item-level stop-sales call
(endpoint confirmed to exist; exact path/schema not yet captured in this
Sprint's contract_loader.py -- add it there first, alongside the price/stock
item-level endpoints, before implementing this class's real call path).
TODO(Phase 2C, CTO GATE): confirm Naver's deactivation mechanism before this
platform ever reaches Stage 3 of the staged rollout -- see
SECURITY_COMPLIANCE_GATE.md §11 gate #11.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from modules.commerce.audit_logger import AuditLogger

# Per-platform confirmed rollback capability, mirroring the evidence matrix.
ROLLBACK_CAPABILITY = {
    "coupang": {
        "confirmed": True,
        "mechanism": "item-level stop-sales endpoint (판매중지)",
        "evidence": "PLATFORM_API_EVIDENCE_MATRIX.md §2.5 (CONFIRMED existence, exact endpoint path not yet captured)",
    },
    "smartstore": {
        "confirmed": False,
        "mechanism": None,
        "evidence": "UNKNOWN -- must be confirmed before this platform enters a real-registration stage",
    },
}


class RollbackManager:
    def __init__(self, audit_logger: Optional[AuditLogger] = None) -> None:
        self.audit_logger = audit_logger or AuditLogger()

    def rollback_capability(self, platform: str) -> Dict[str, Any]:
        return dict(ROLLBACK_CAPABILITY.get(str(platform or "").strip().lower(), {
            "confirmed": False,
            "mechanism": None,
            "evidence": "unknown platform",
        }))

    def request_rollback(
        self,
        platform: str,
        listing_reference: Optional[str],
        reason: str,
    ) -> Dict[str, Any]:
        """Record a rollback request. Always dry-run in Phase 2A -- never
        calls a real endpoint, regardless of `rollback_capability()`'s
        answer, since Phase 2A has no real listing to roll back in the first
        place (nothing this Sprint can create was ever actually submitted)."""
        capability = self.rollback_capability(platform)

        result = {
            "platform": platform,
            "listing_reference": listing_reference,
            "reason": reason,
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "executed": False,
            "mode": "dry_run",
            "capability": capability,
            "note": (
                "Phase 2A never performs a real submission, so there is nothing live to roll back. "
                "This call only records the rollback *intent* for audit/design-review purposes."
            ),
        }

        self.audit_logger.log({
            "type": "rollback_requested",
            "platform": platform,
            "listing_reference": listing_reference,
            "reason": reason,
            "executed": False,
            "capability_confirmed": capability.get("confirmed", False),
        })

        return result
