"""Commerce Phase 2A — Approval Gate.

"Approval First" enforcement: reads `config/commerce/approval.json` and
answers exactly one question per call -- "is capability X approved for
platform Y right now?" It never grants an approval itself; it only reports
what a human has already recorded in the config file.

Design basis:
- `docs/COMMERCE_PHASE_1_CONTRACT.md` §9 ("explicit decision on whether
  listing creation, update, inventory, price, and order scopes are
  individually allowed").
- `docs/RESEARCH/COMMERCE/SECURITY_COMPLIANCE_GATE.md` §11 gate #6 ("the
  single most load-bearing gate ... explicit per-capability scope approval").

Hard rule for Phase 2A: regardless of what this file reports, no adapter's
`submit()` may ever perform a real network call this Sprint (see
`marketplace_base.py` / `smartstore_adapter.py` / `coupang_adapter.py`) --
this gate is necessary-but-not-sufficient defense in depth, never the sole
reason a real call would be allowed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_APPROVAL_PATH = Path("config/commerce/approval.json")

# Mirrors docs/COMMERCE_PHASE_1_CONTRACT.md §9's exact capability list --
# never a different or broader set.
CAPABILITIES = ("listing_creation", "listing_update", "inventory_update", "price_update", "order_actions")


class ApprovalGate:
    def __init__(self, approval_path: Optional[Path] = None) -> None:
        self.approval_path = Path(approval_path or DEFAULT_APPROVAL_PATH)

    def load(self) -> Dict[str, Any]:
        """Read the approval config. Fail closed: any read/parse error, or a
        missing file, is treated as "nothing is approved" -- never as
        "approved by default"."""
        try:
            with open(self.approval_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception as error:
            print(f"Commerce Approval Gate: could not read {self.approval_path}: {error}")

        return self._closed_default()

    def is_capability_approved(
        self,
        capability: str,
        *,
        platform: Optional[str] = None,
        product_id: Optional[str] = None,
        payload_hash: Optional[str] = None,
        approval_id: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> bool:
        return self.check(
            capability,
            platform=platform,
            product_id=product_id,
            payload_hash=payload_hash,
            approval_id=approval_id,
            now=now,
        )["approved"]

    def check(
        self,
        capability: str,
        *,
        platform: Optional[str] = None,
        product_id: Optional[str] = None,
        payload_hash: Optional[str] = None,
        approval_id: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Return a full, explainable decision, not just a bool -- so callers
        (and the audit log) always have a `reason`, matching this project's
        "never a silent True/False" convention."""
        if capability not in CAPABILITIES:
            return self._decision(capability, "unknown_capability", f"Unknown capability: {capability!r}.")

        config = self.load()
        gate_value = config.get("phase_2_cto_gate_satisfied")
        if not isinstance(gate_value, bool):
            return self._decision(
                capability,
                "invalid_approval_boolean",
                "phase_2_cto_gate_satisfied must be the JSON boolean true or false.",
            )
        if gate_value is not True:
            return self._decision(
                capability,
                "cto_gate_not_satisfied",
                "The Phase 2 CTO gate is not satisfied.",
            )

        scopes = config.get("approved_capabilities")
        if not isinstance(scopes, dict) or not isinstance(scopes.get(capability), bool):
            return self._decision(
                capability,
                "invalid_approval_boolean",
                f"The '{capability}' scope must be an explicit JSON boolean.",
            )
        if scopes[capability] is not True:
            return self._decision(
                capability,
                "capability_not_approved",
                f"The '{capability}' scope is not approved.",
            )

        target = {
            "platform": platform,
            "product_id": product_id,
            "payload_hash": payload_hash,
            "approval_id": approval_id,
        }
        if any(not isinstance(value, str) or not value.strip() for value in target.values()):
            return self._decision(
                capability,
                "missing_approval_target",
                "Approval checks require platform, product_id, payload_hash, and approval_id.",
            )

        identity = config.get("approval_identity")
        if not isinstance(identity, dict):
            return self._decision(
                capability,
                "missing_approval_identity",
                "approval_identity is required and must bind the approved target.",
            )

        for field, expected in target.items():
            recorded = identity.get(field)
            if not isinstance(recorded, str) or not recorded.strip() or recorded != expected:
                return self._decision(
                    capability,
                    "approval_target_mismatch",
                    f"Approval evidence does not match the execution target field '{field}'.",
                )

        issued_at = self._parse_time(identity.get("issued_at"))
        expires_at = self._parse_time(identity.get("expires_at"))
        if issued_at is None or expires_at is None or expires_at <= issued_at:
            return self._decision(
                capability,
                "invalid_approval_expiry",
                "Approval evidence requires valid timezone-aware issued_at and expires_at values.",
            )

        evaluated_at = now or datetime.now(timezone.utc)
        if evaluated_at.tzinfo is None:
            return self._decision(
                capability,
                "invalid_evaluation_time",
                "Approval evaluation time must include a timezone.",
            )
        evaluated_at = evaluated_at.astimezone(timezone.utc)
        if evaluated_at < issued_at:
            return self._decision(
                capability,
                "approval_not_yet_valid",
                "Approval evidence is not valid yet.",
            )
        if evaluated_at >= expires_at:
            return self._decision(
                capability,
                "approval_expired",
                "Approval evidence has expired.",
            )

        return self._decision(
            capability,
            "approved",
            f"The '{capability}' scope is approved for the exact target.",
            approved=True,
            approval_id=identity["approval_id"],
        )

    @staticmethod
    def _parse_time(value: Any) -> Optional[datetime]:
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _decision(
        capability: str,
        reason_code: str,
        reason: str,
        *,
        approved: bool = False,
        approval_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        decision = {
            "capability": capability,
            "approved": approved,
            "reason_code": reason_code,
            "reason": reason,
        }
        if approval_id is not None:
            decision["approval_id"] = approval_id
        return decision

    @staticmethod
    def _closed_default() -> Dict[str, Any]:
        return {
            "phase_2_cto_gate_satisfied": False,
            "approved_capabilities": {capability: False for capability in CAPABILITIES},
            "approval_identity": None,
            "reason": "approval.json missing or unreadable -- defaulted closed.",
        }
