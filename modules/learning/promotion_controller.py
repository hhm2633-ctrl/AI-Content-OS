"""Owner approval gate for PatternRegistry promotion."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from modules.analytics_engine.promotion_candidate_builder import (
    PromotionCandidateBuilder,
    PromotionCandidateError,
)
from modules.knowledge.pattern_registry import PatternRegistry


class PromotionControllerError(ValueError):
    pass


class PromotionController:
    def __init__(
        self,
        candidate_path: Optional[Path] = None,
        registry: Optional[PatternRegistry] = None,
    ):
        self.builder = PromotionCandidateBuilder(candidate_path)
        self.registry = registry or PatternRegistry()

    def review(
        self,
        promotion_candidate_id: str,
        *,
        owner_approved: bool,
        approved_by: str,
        note: str = "",
    ) -> Dict[str, Any]:
        approved_by = str(approved_by or "").strip()
        if not approved_by:
            raise PromotionControllerError("approved_by is required")
        data = self.builder.load()
        candidate = self._find(data, promotion_candidate_id)
        candidate["owner_approval"] = {
            "approved": owner_approved is True,
            "approved_by": approved_by,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "note": str(note or "").strip(),
        }
        candidate["status"] = "owner_approved" if owner_approved is True else "owner_rejected"
        candidate["pattern_registry_called"] = False
        self.builder.save(data)
        return dict(candidate)

    def promote_approved(self, promotion_candidate_id: str, pattern: Any) -> Any:
        data = self.builder.load()
        candidate = self._find(data, promotion_candidate_id)
        if candidate.get("measurement_class") != "external_measured":
            raise PromotionControllerError("internal proxy evidence cannot promote patterns")
        if candidate.get("performance_met") is not True:
            raise PromotionControllerError("promotion candidate has not met measured performance gates")
        approval = candidate.get("owner_approval") or {}
        if approval.get("approved") is not True or not approval.get("approved_by"):
            raise PromotionControllerError("explicit owner approval is required before promotion")
        if candidate.get("status") != "owner_approved":
            raise PromotionControllerError("promotion candidate is not in owner_approved state")

        promoted = self.registry.promote(
            pattern,
            performance_met=True,
            human_approved=True,
        )
        candidate["status"] = "promoted"
        candidate["pattern_registry_called"] = True
        candidate["promoted_at"] = datetime.now(timezone.utc).isoformat()
        self.builder.save(data)
        return promoted

    @staticmethod
    def _find(data: Dict[str, Any], promotion_candidate_id: str) -> Dict[str, Any]:
        for candidate in data.get("candidates", []):
            if candidate.get("promotion_candidate_id") == promotion_candidate_id:
                return candidate
        raise PromotionControllerError(
            f"unknown promotion_candidate_id: {promotion_candidate_id}"
        )
