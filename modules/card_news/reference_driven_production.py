"""Fail-closed orchestration for Reference V2 slide production."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from modules.card_news.reference_blueprint_adapter import (
    ReferenceBlueprintAdapter,
)
from modules.card_news.reference_content_fit import ReferenceContentFitChecker
from modules.design_learning.layout_blueprint_contract import (
    LayoutBlueprintValidationError,
    validate_layout_blueprint,
)
from modules.design_learning.reference_recipe_selector import (
    ReferenceRecipeSelector,
)
from modules.design_learning.reference_specimen_registry import (
    ReferenceSpecimenRegistry,
    ReferenceSpecimenValidationError,
)


SCHEMA_VERSION = "reference-driven-production.v2"


def _json_copy(value: Any) -> Any:
    return json.loads(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
        )
    )


def _blocked(reason_code: str, **details: Any) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "blocked",
        "outcome": "blocked",
        "reason_code": reason_code,
        "legacy_renderer_fallback_allowed": False,
        **details,
    }


class ReferenceDrivenProductionOrchestrator:
    """Connect the complete Reference V2 contract without a legacy fallback."""

    def __init__(self) -> None:
        self._selector = ReferenceRecipeSelector()
        self._fit_checker = ReferenceContentFitChecker()
        self._adapter = ReferenceBlueprintAdapter()

    def produce(
        self,
        *,
        specimens: Sequence[Mapping[str, Any]],
        blueprints: Mapping[str, Mapping[str, Any]],
        context: Mapping[str, Any],
        content: Mapping[str, Any],
        media: Any,
    ) -> dict[str, Any]:
        try:
            safe_input = _json_copy(
                {
                    "specimens": specimens,
                    "blueprints": blueprints,
                    "context": context,
                    "content": content,
                    "media": media,
                }
            )
        except (TypeError, ValueError) as exc:
            return _blocked(
                "input_not_json_safe",
                errors=[{"code": "input_not_json_safe", "message": str(exc)}],
            )

        try:
            registry = ReferenceSpecimenRegistry(safe_input["specimens"])
        except (ReferenceSpecimenValidationError, TypeError, ValueError) as exc:
            return _blocked(
                "specimen_registry_rejected",
                errors=[{"code": "invalid_specimen", "message": str(exc)}],
            )

        selectable = [
            specimen
            for specimen in registry.selectable()
            if specimen.get("reference_only") is False
        ]
        if not selectable:
            return _blocked("no_owner_approved_production_specimen")

        validated_blueprints: dict[str, dict[str, Any]] = {}
        blueprint_errors: list[dict[str, str]] = []
        for specimen in selectable:
            blueprint_id = specimen["blueprint_id"]
            raw_blueprint = safe_input["blueprints"].get(blueprint_id)
            if not isinstance(raw_blueprint, Mapping):
                blueprint_errors.append(
                    {
                        "reference_id": specimen["reference_id"],
                        "blueprint_id": blueprint_id,
                        "code": "blueprint_missing",
                    }
                )
                continue
            try:
                blueprint = validate_layout_blueprint(raw_blueprint)
            except LayoutBlueprintValidationError as exc:
                blueprint_errors.append(
                    {
                        "reference_id": specimen["reference_id"],
                        "blueprint_id": blueprint_id,
                        "code": "blueprint_invalid",
                        "message": str(exc),
                    }
                )
                continue
            provenance_reference_id = (
                blueprint.get("provenance", {}).get("reference_id")
                if isinstance(blueprint.get("provenance"), Mapping)
                else None
            )
            if provenance_reference_id != specimen["reference_id"]:
                blueprint_errors.append(
                    {
                        "reference_id": specimen["reference_id"],
                        "blueprint_id": blueprint_id,
                        "code": "blueprint_reference_mismatch",
                    }
                )
                continue
            blueprint["reference_id"] = specimen["reference_id"]
            validated_blueprints[blueprint_id] = blueprint

        selector_blueprints = _json_copy(validated_blueprints)
        for selector_blueprint in selector_blueprints.values():
            selector_blueprint["blueprint_version"] = str(
                selector_blueprint["blueprint_version"]
            )
        selector_context = dict(safe_input["context"])
        media_rows = safe_input["media"]
        selector_context.setdefault(
            "media_count",
            len(media_rows) if isinstance(media_rows, list) else 0,
        )
        selector_context.setdefault(
            "copy_char_count",
            len(str(safe_input["content"].get("headline") or ""))
            + len(str(safe_input["content"].get("body") or "")),
        )
        selection = self._selector.select(
            specimens=selectable,
            blueprints=selector_blueprints,
            context=selector_context,
        )
        if selection.get("status") != "selected":
            return _blocked(
                selection.get("reason_code")
                or "no_compatible_owner_approved_reference",
                selection=selection,
                blueprint_errors=blueprint_errors,
            )

        selected_specimen = registry.require_selectable(
            selection["primary_reference_id"]
        )
        if selected_specimen.get("reference_only") is not False:
            return _blocked(
                "reference_only_not_production_selectable",
                selection=selection,
            )
        blueprint = validated_blueprints[selection["primary_blueprint_id"]]
        fit_result = self._fit_checker.evaluate(
            blueprint,
            safe_input["content"],
            safe_input["media"],
            slide_role=safe_input["context"].get("slide_role"),
        )
        if fit_result.get("outcome") != "fit":
            outcome = fit_result.get("outcome") or "blocked"
            return {
                "schema_version": SCHEMA_VERSION,
                "status": outcome,
                "outcome": outcome,
                "reason_code": f"content_fit_{outcome}",
                "legacy_renderer_fallback_allowed": False,
                "selection": selection,
                "owner_approval_receipt_id": selected_specimen[
                    "owner_approval_receipt_id"
                ],
                "geometry_hash": blueprint["geometry_hash"],
                "fit_result": fit_result,
                "blueprint_errors": blueprint_errors,
            }

        adapted = self._adapter.adapt(
            blueprint,
            safe_input["content"],
            safe_input["media"],
            selection=selection,
            fit_result=fit_result,
        )
        if adapted.get("status") != "adapted":
            return _blocked(
                "reference_blueprint_adapter_blocked",
                selection=selection,
                fit_result=fit_result,
                adapter_result=adapted,
            )

        receipt = dict(adapted["reference_consumption_receipt"])
        receipt["owner_approval_receipt_id"] = selected_specimen[
            "owner_approval_receipt_id"
        ]
        return _json_copy(
            {
                "schema_version": SCHEMA_VERSION,
                "status": "ready",
                "outcome": "fit",
                "reason_code": "reference_v2_ready",
                "legacy_renderer_fallback_allowed": False,
                "selection": selection,
                "owner_approval_receipt_id": selected_specimen[
                    "owner_approval_receipt_id"
                ],
                "geometry_hash": blueprint["geometry_hash"],
                "fit_result": fit_result,
                "adapted_slide": {
                    **adapted,
                    "reference_consumption_receipt": receipt,
                },
                "blueprint_errors": blueprint_errors,
            }
        )


def produce_reference_driven_slide(
    *,
    specimens: Sequence[Mapping[str, Any]],
    blueprints: Mapping[str, Mapping[str, Any]],
    context: Mapping[str, Any],
    content: Mapping[str, Any],
    media: Any,
) -> dict[str, Any]:
    """Functional JSON-safe entry point for one slide."""

    return ReferenceDrivenProductionOrchestrator().produce(
        specimens=specimens,
        blueprints=blueprints,
        context=context,
        content=content,
        media=media,
    )


__all__ = [
    "ReferenceDrivenProductionOrchestrator",
    "SCHEMA_VERSION",
    "produce_reference_driven_slide",
]
