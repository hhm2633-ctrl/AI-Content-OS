"""Commerce Phase 2A — Marketplace Adapter Interface.

Abstract base class every platform adapter (`smartstore_adapter.py`,
`coupang_adapter.py`) must implement. Interface-first design: this defines the
*shape* every adapter will eventually have (including the real-submission
path), while making that real path structurally unreachable in Phase 2A.

Design basis: `docs/COMMERCE_PHASE_2_UPLOAD_ARCHITECTURE.md` §3.1-§3.3 (Adapter
structure between Phase 1 output and platform APIs; SmartStoreAdapter/
CoupangAdapter responsibilities).

Hard rule (Fail Closed + Dry Run First, this Sprint's explicit constraint):
`submit()` is implemented ONCE, here, in the base class, as an unconditional
block -- no subclass overrides it. A subclass that wanted to bypass this would
have to explicitly delete/replace this method, which is a loud, reviewable
change, not a silent one. This is deliberately stricter than "subclasses
should not implement submit() yet."
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from modules.commerce.approval_gate import ApprovalGate
from modules.commerce.audit_logger import AuditLogger
from modules.commerce.credential_manager import CredentialManager
from modules.commerce.payload_builder import build_payload, summarize_gaps
from modules.commerce.schema_validator import validate_payload


class RealApiCallBlockedError(Exception):
    """Raised by `submit()` in every Phase 2A adapter. This is not a bug to be
    caught and worked around -- it is the entire point of this Sprint's
    dry-run-only constraint. A caller who catches this and tries again with
    different arguments is misusing this class."""


class MarketplaceAdapterBase(ABC):
    """Common orchestration for every platform adapter.

    Subclasses provide `platform_name` and may override `_platform_specific_checks()`
    for platform-only validation (e.g. Coupang's item-centric options[] shape),
    but never override `submit()`.
    """

    def __init__(
        self,
        credential_manager: Optional[CredentialManager] = None,
        approval_gate: Optional[ApprovalGate] = None,
        audit_logger: Optional[AuditLogger] = None,
    ) -> None:
        self.credential_manager = credential_manager or CredentialManager()
        self.approval_gate = approval_gate or ApprovalGate()
        self.audit_logger = audit_logger or AuditLogger()

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """e.g. 'smartstore' or 'coupang' -- must match contract_loader.py's keys."""

    def build_payload(self, commerce_result: Dict[str, Any]) -> Dict[str, Any]:
        """Build a dry-run payload from a Phase 1 `commerce_result`. Pure,
        delegates entirely to `payload_builder.py` -- no platform-specific
        payload logic lives in the adapter itself, so the same builder logic
        is exercised identically for every platform."""
        payload = build_payload(self.platform_name, commerce_result)
        gaps = summarize_gaps(payload)

        self.audit_logger.log_payload_built(
            platform=self.platform_name,
            request_id=commerce_result.get("request_id") if isinstance(commerce_result, dict) else None,
            gaps=gaps,
            idempotency_key=self._idempotency_key(commerce_result),
        )

        return payload

    def validate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a built payload. Delegates to `schema_validator.py`."""
        result = validate_payload(self.platform_name, payload)
        platform_result = self._platform_specific_checks(payload, result)

        self.audit_logger.log_validation(
            platform=self.platform_name,
            request_id=payload.get("phase1_request_id") if isinstance(payload, dict) else None,
            valid=platform_result.valid,
            blocked_reason_count=len(platform_result.blocked_reasons),
        )

        return platform_result.to_dict()

    def dry_run(self, commerce_result: Dict[str, Any]) -> Dict[str, Any]:
        """Build + validate in one call, plus a credential/approval status
        readout. Never touches the network. This is the primary Phase 2A
        entry point -- see `dry_run_executor.py` for the full orchestrated
        pipeline (this method alone is also directly usable/testable)."""
        payload = self.build_payload(commerce_result)
        validation = self.validate(payload)

        return {
            "platform": self.platform_name,
            "mode": "dry_run",
            "payload": payload,
            "validation": validation,
            "credential_status": self.credential_manager.get_credential_status(self.platform_name),
            "approval_status": {
                capability: self.approval_gate.check(capability)
                for capability in ("listing_creation", "listing_update", "inventory_update", "price_update")
            },
            "network_call_made": False,
        }

    def submit(self, *_args: Any, **_kwargs: Any) -> None:
        """Unconditionally blocked in Phase 2A. See class docstring.

        TODO(Phase 2B, CTO GATE required): implement real submission ONLY
        after: (1) credentials are real and confirmed working against a
        sandbox or the platform's own validation path, (2) `approval_gate`
        reports the relevant capability approved, (3) the Phase 2 CTO gate
        checklist (`docs/RESEARCH/COMMERCE/SECURITY_COMPLIANCE_GATE.md` §11)
        is satisfied. Even then, per that document's Stage 3, every single
        submission requires individual human approval -- this method should
        never become a silent batch-submit path.
        """
        self.audit_logger.log_submit_blocked(
            platform=self.platform_name,
            reason="Commerce Phase 2A: real API submission is unconditionally blocked this Sprint.",
        )
        raise RealApiCallBlockedError(
            f"{self.platform_name}: real API submission is not implemented in Commerce Phase 2A. "
            "This Sprint is dry-run only by explicit instruction -- see marketplace_base.py."
        )

    def _platform_specific_checks(self, payload: Dict[str, Any], result: Any) -> Any:
        """Hook for adapter-specific validation beyond the generic contract
        check. Default: no additional checks. Subclasses may extend `result`
        (a `schema_validator.ValidationResult`) in place and return it."""
        return result

    def _idempotency_key(self, commerce_result: Dict[str, Any]) -> Optional[str]:
        """Deterministic idempotency key from stable fields only -- never a
        timestamp. Mirrors the principle already established in
        `docs/RESEARCH/COMMERCE/ORDER_FULFILLMENT_STATE_MACHINE.md` §4.

        Instance method (not static): `commerce_result` has no per-platform
        product identifier of its own (CONFIRMED -- CommerceModule's result
        has no `verified_product_facts`/product-id field at all), so the best
        available stable proxy is this adapter's own platform_packages entry's
        `product_name`, which is deterministic per Phase 1 run and platform.
        """
        if not isinstance(commerce_result, dict):
            return None

        request_id = str(commerce_result.get("request_id") or "")
        packages = commerce_result.get("platform_packages")
        package = packages.get(self.platform_name) if isinstance(packages, dict) else None
        product_id = str(package.get("product_name") or "") if isinstance(package, dict) else ""

        if not request_id and not product_id:
            return None

        digest_input = f"{request_id}:{product_id}".encode("utf-8")
        return "sha256:" + hashlib.sha256(digest_input).hexdigest()
