"""Bind fitted slide content to immutable reference-blueprint geometry."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Mapping, Optional, Sequence


REQUIRED_IDENTITY_FIELDS = (
    "reference_id",
    "blueprint_id",
    "blueprint_version",
    "geometry_hash",
)
MEDIA_ROLES = {"primary_media", "secondary_media"}


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


class ReferenceBlueprintAdapter:
    """Create explicit bindings without reconstructing or repairing geometry."""

    def adapt(
        self,
        blueprint: Mapping[str, Any],
        content: Optional[Mapping[str, Any]] = None,
        media: Optional[Any] = None,
        *,
        selection: Optional[Mapping[str, Any]] = None,
        fit_result: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        blueprint = _as_mapping(blueprint)
        selection = _as_mapping(selection)
        content = _as_mapping(content)
        errors = self._identity_errors(blueprint, selection)
        regions = _as_sequence(blueprint.get("regions"))
        errors.extend(self._geometry_errors(regions))

        if fit_result is not None:
            fit_result = _as_mapping(fit_result)
            if fit_result.get("outcome") != "fit" or fit_result.get("fit") is False:
                errors.append(
                    {
                        "code": "content_fit_not_passed",
                        "outcome": fit_result.get("outcome"),
                    }
                )

        content_bindings, media_bindings, binding_errors = self._build_bindings(
            regions=regions,
            content=content,
            media=media,
        )
        errors.extend(binding_errors)

        identity = self._identity(blueprint, selection)
        if errors:
            return {
                "status": "blocked",
                "outcome": "blocked",
                **identity,
                "regions": deepcopy(list(regions)),
                "style_tokens": deepcopy(blueprint.get("style_tokens", {})),
                "content_bindings": content_bindings,
                "media_bindings": media_bindings,
                "errors": errors,
                "reference_consumption_receipt": {
                    **identity,
                    "status": "blocked",
                    "bound_region_ids": [],
                    "geometry_modified": False,
                },
            }

        bound_region_ids = [
            binding["region_id"] for binding in content_bindings + media_bindings
        ]
        return {
            "status": "adapted",
            "outcome": "fit",
            **identity,
            "regions": deepcopy(list(regions)),
            "style_tokens": deepcopy(blueprint.get("style_tokens", {})),
            "content_bindings": content_bindings,
            "media_bindings": media_bindings,
            "reference_consumption_receipt": {
                **identity,
                "status": "binding_complete",
                "bound_region_ids": bound_region_ids,
                "geometry_region_ids": [
                    _as_mapping(region).get("region_id") for region in regions
                ],
                "geometry_modified": False,
            },
        }

    def build(
        self,
        blueprint: Mapping[str, Any],
        content: Optional[Mapping[str, Any]] = None,
        media: Optional[Any] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Compatibility alias for render-request assembly callers."""

        return self.adapt(blueprint, content, media, **kwargs)

    @staticmethod
    def _identity(
        blueprint: Mapping[str, Any],
        selection: Mapping[str, Any],
    ) -> Dict[str, Any]:
        return {
            "primary_reference_id": selection.get("primary_reference_id")
            or blueprint.get("reference_id"),
            "reference_id": blueprint.get("reference_id")
            or selection.get("primary_reference_id"),
            "blueprint_id": blueprint.get("blueprint_id"),
            "blueprint_version": blueprint.get("blueprint_version"),
            "geometry_hash": blueprint.get("geometry_hash"),
        }

    def _identity_errors(
        self,
        blueprint: Mapping[str, Any],
        selection: Mapping[str, Any],
    ) -> List[Dict[str, Any]]:
        identity = self._identity(blueprint, selection)
        errors = [
            {"code": "missing_identity", "field": field}
            for field in REQUIRED_IDENTITY_FIELDS
            if not identity.get(field)
        ]
        selected_reference = selection.get("primary_reference_id")
        selected_blueprint = selection.get("primary_blueprint_id")
        if (
            selected_reference
            and blueprint.get("reference_id")
            and selected_reference != blueprint.get("reference_id")
        ):
            errors.append(
                {
                    "code": "reference_identity_mismatch",
                    "selected": selected_reference,
                    "blueprint": blueprint.get("reference_id"),
                }
            )
        if (
            selected_blueprint
            and blueprint.get("blueprint_id")
            and selected_blueprint != blueprint.get("blueprint_id")
        ):
            errors.append(
                {
                    "code": "blueprint_identity_mismatch",
                    "selected": selected_blueprint,
                    "blueprint": blueprint.get("blueprint_id"),
                }
            )
        return errors

    @staticmethod
    def _geometry_errors(regions: Sequence[Any]) -> List[Dict[str, Any]]:
        if not regions:
            return [{"code": "missing_geometry", "reason": "regions_missing"}]
        errors: List[Dict[str, Any]] = []
        seen_ids = set()
        for index, raw_region in enumerate(regions):
            region = _as_mapping(raw_region)
            region_id = region.get("region_id")
            box = _as_sequence(region.get("box_norm"))
            if not region_id or region_id in seen_ids:
                errors.append(
                    {
                        "code": "invalid_geometry",
                        "region_index": index,
                        "reason": "missing_or_duplicate_region_id",
                    }
                )
            seen_ids.add(region_id)
            if len(box) != 4:
                errors.append(
                    {
                        "code": "invalid_geometry",
                        "region_id": region_id,
                        "reason": "box_norm_missing",
                    }
                )
                continue
            try:
                x, y, width, height = (float(value) for value in box)
            except (TypeError, ValueError):
                errors.append(
                    {
                        "code": "invalid_geometry",
                        "region_id": region_id,
                        "reason": "box_norm_non_numeric",
                    }
                )
                continue
            if (
                x < 0
                or y < 0
                or width <= 0
                or height <= 0
                or x + width > 1
                or y + height > 1
            ):
                errors.append(
                    {
                        "code": "invalid_geometry",
                        "region_id": region_id,
                        "reason": "box_norm_out_of_bounds",
                    }
                )
        return errors

    @staticmethod
    def _media_by_role(media: Any) -> Dict[str, List[Mapping[str, Any]]]:
        grouped: Dict[str, List[Mapping[str, Any]]] = {
            "primary_media": [],
            "secondary_media": [],
        }
        if isinstance(media, Mapping):
            for role in MEDIA_ROLES:
                raw_assets = media.get(role)
                if isinstance(raw_assets, Mapping):
                    grouped[role] = [raw_assets]
                else:
                    grouped[role] = [
                        asset
                        for asset in _as_sequence(raw_assets)
                        if isinstance(asset, Mapping)
                    ]
            if not any(grouped.values()) and media:
                role = str(media.get("role") or "primary_media")
                grouped.setdefault(role, []).append(media)
        else:
            for asset in _as_sequence(media):
                if not isinstance(asset, Mapping):
                    continue
                role = str(asset.get("role") or "primary_media")
                grouped.setdefault(role, []).append(asset)
        return grouped

    def _build_bindings(
        self,
        *,
        regions: Sequence[Any],
        content: Mapping[str, Any],
        media: Any,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        content_bindings: List[Dict[str, Any]] = []
        media_bindings: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        media_by_role = self._media_by_role(media)
        media_offsets: Dict[str, int] = {role: 0 for role in MEDIA_ROLES}

        explicit_by_region = _as_mapping(content.get("by_region"))
        for raw_region in regions:
            region = _as_mapping(raw_region)
            region_id = region.get("region_id")
            role = str(region.get("role") or "")
            if role == "accent":
                continue
            if role in MEDIA_ROLES:
                index = media_offsets.get(role, 0)
                assets = media_by_role.get(role, [])
                asset = assets[index] if index < len(assets) else None
                media_offsets[role] = index + 1
                if asset is not None:
                    media_bindings.append(
                        {
                            "region_id": region_id,
                            "role": role,
                            "asset": deepcopy(dict(asset)),
                        }
                    )
                elif region.get("required"):
                    errors.append(
                        {
                            "code": "missing_required_media_binding",
                            "region_id": region_id,
                            "role": role,
                        }
                    )
                continue

            value = (
                explicit_by_region.get(region_id)
                if region_id in explicit_by_region
                else content.get(role)
            )
            if value not in (None, "", [], {}):
                content_bindings.append(
                    {
                        "region_id": region_id,
                        "role": role,
                        "content": deepcopy(value),
                    }
                )
            elif region.get("required"):
                errors.append(
                    {
                        "code": "missing_required_content_binding",
                        "region_id": region_id,
                        "role": role,
                    }
                )
        return content_bindings, media_bindings, errors


def adapt_reference_blueprint(
    blueprint: Mapping[str, Any],
    content: Optional[Mapping[str, Any]] = None,
    media: Optional[Any] = None,
    *,
    selection: Optional[Mapping[str, Any]] = None,
    fit_result: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Functional entry point for a single fitted slide."""

    return ReferenceBlueprintAdapter().adapt(
        blueprint,
        content,
        media,
        selection=selection,
        fit_result=fit_result,
    )
