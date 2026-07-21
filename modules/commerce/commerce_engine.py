"""Commerce Phase 2A — Commerce Engine (top-level facade).

Ties together Commerce Phase 1's existing, unmodified `CommerceModule` output
with the Phase 2A dry-run skeleton (adapters, payload builder, validator,
approval gate, dry-run executor, audit logger). This is the single entry point
a future caller (a CLI, a test, or eventually an operator UI per
`docs/RESEARCH/COMMERCE/MANUS_FARMERSGO_INTEGRATION_PLAN.md`'s UX-pattern
notes) is expected to use.

Explicitly NOT wired into `src/workflow_engine.py` -- Commerce (both Phase 1
and this Phase 2A skeleton) remains a standalone, on-demand system, exactly
like `modules/competitor_learning/` already is in this project. This module
does not change that.

Explicitly does not perform any real API call -- every platform interaction
this engine can trigger terminates at `DryRunExecutor`/`MarketplaceAdapterBase.dry_run()`.
`run_full_dry_run()` is the only "do everything" entry point, and it never
calls `adapter.submit()`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from modules.commerce.approval_gate import ApprovalGate
from modules.commerce.audit_logger import AuditLogger
from modules.commerce.commerce_module import CommerceModule
from modules.commerce.coupang_adapter import CoupangAdapter
from modules.commerce.credential_manager import CredentialManager
from modules.commerce.dry_run_executor import DryRunExecutor
from modules.commerce.rollback_manager import RollbackManager
from modules.commerce.smartstore_adapter import SmartStoreAdapter

VERSION = "commerce_phase_2a.0"

_ADAPTER_CLASSES = {
    "smartstore": SmartStoreAdapter,
    "coupang": CoupangAdapter,
}


class CommerceEngine:
    """Phase 2A orchestrator. Composition, not inheritance: this class does
    not subclass `CommerceModule` -- Phase 1 remains completely untouched and
    independently usable; this engine only *consumes* its output."""

    def __init__(
        self,
        commerce_module: Optional[CommerceModule] = None,
        credential_manager: Optional[CredentialManager] = None,
        approval_gate: Optional[ApprovalGate] = None,
        audit_logger: Optional[AuditLogger] = None,
        dry_run_executor: Optional[DryRunExecutor] = None,
        rollback_manager: Optional[RollbackManager] = None,
    ) -> None:
        self.commerce_module = commerce_module or CommerceModule()
        self.credential_manager = credential_manager or CredentialManager()
        self.approval_gate = approval_gate or ApprovalGate()
        self.audit_logger = audit_logger or AuditLogger()
        self.dry_run_executor = dry_run_executor or DryRunExecutor(audit_logger=self.audit_logger)
        self.rollback_manager = rollback_manager or RollbackManager(audit_logger=self.audit_logger)

    def _build_adapter(self, platform: str):
        adapter_class = _ADAPTER_CLASSES.get(str(platform or "").strip().lower())

        if adapter_class is None:
            raise ValueError(f"Unsupported platform: {platform!r}. Supported: {sorted(_ADAPTER_CLASSES)}")

        return adapter_class(
            credential_manager=self.credential_manager,
            approval_gate=self.approval_gate,
            audit_logger=self.audit_logger,
        )

    def run_full_dry_run(
        self,
        commerce_result: Dict[str, Any],
        platforms: Optional[List[str]] = None,
        persist: bool = True,
    ) -> Dict[str, Any]:
        """Run the Phase 2A dry-run pipeline for every requested platform
        against an already-generated Phase 1 `commerce_result`.

        Never calls Phase 1 itself -- the caller is responsible for having
        already run `CommerceModule.run()` (or an equivalent
        `ready_for_manual_upload`-gated result). This keeps Phase 1's own
        truth/source/freshness gating as the single point of product-fact
        authority; this engine never re-derives or second-guesses it.
        """
        platforms = platforms or list(_ADAPTER_CLASSES)
        results: Dict[str, Any] = {}

        for platform in platforms:
            try:
                adapter = self._build_adapter(platform)
                results[platform] = self.dry_run_executor.run(adapter, commerce_result, persist=persist)
            except Exception as error:
                results[platform] = {
                    "platform": platform,
                    "mode": "dry_run",
                    "error": str(error),
                    "network_call_made": False,
                }

        overall_ready = all(
            isinstance(result.get("validation"), dict) and result["validation"].get("valid")
            for result in results.values()
            if "error" not in result
        ) and bool(results)

        return {
            "module": "CommerceEngine",
            "phase": "commerce_phase_2a",
            "version": VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "phase1_request_id": commerce_result.get("request_id") if isinstance(commerce_result, dict) else None,
            "phase1_status": commerce_result.get("status") if isinstance(commerce_result, dict) else None,
            "platforms": results,
            "overall_dry_run_ready": overall_ready,
            "upload_mode": "dry_run_only",
            "auto_upload_performed": False,
            "capability_boundaries": {
                "network_calls": False,
                "platform_upload": False,
                "browser_automation": False,
                "credential_access": False,
            },
        }

    def run_from_facts(
        self,
        product_facts: Optional[Dict[str, Any]],
        platforms: Optional[List[str]] = None,
        content_patterns: Optional[Dict[str, Any]] = None,
        learned_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Convenience path: run Phase 1 (`CommerceModule.run()`, unmodified)
        and then this engine's Phase 2A dry-run pipeline in one call. Phase 1
        persistence behavior is untouched (`persist=True` by default inside
        `CommerceModule`); this is purely a convenience composition, not a new
        code path inside Phase 1 itself."""
        commerce_result = self.commerce_module.run(
            product_facts=product_facts,
            content_patterns=content_patterns,
            learned_context=learned_context,
        )

        dry_run_summary = self.run_full_dry_run(commerce_result, platforms=platforms)

        return {
            "phase1_result": commerce_result,
            "phase2a_result": dry_run_summary,
        }

    def check_approval_status(self) -> Dict[str, Any]:
        """Read-only snapshot of every capability's approval state, for a
        future operator UI or a pre-flight check -- never mutates
        `config/commerce/approval.json`."""
        from modules.commerce.approval_gate import CAPABILITIES

        return {capability: self.approval_gate.check(capability) for capability in CAPABILITIES}
