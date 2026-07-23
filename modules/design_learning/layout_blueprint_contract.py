"""Fail-closed contract for content-free, normalized layout blueprints."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any


SUPPORTED_REGION_ROLES = frozenset(
    {
        "primary_media",
        "secondary_media",
        "headline",
        "subheadline",
        "body",
        "metric",
        "quote",
        "real_comment",
        "source_label",
        "commerce_sticker",
        "cta",
        "account_mark",
        "accent",
    }
)

BLUEPRINT_REQUIRED_FIELDS = frozenset(
    {
        "blueprint_id",
        "blueprint_version",
        "canvas",
        "layout_family",
        "regions",
        "style_tokens",
        "fit_constraints",
        "geometry_hash",
        "provenance",
    }
)

REGION_REQUIRED_FIELDS = frozenset(
    {
        "region_id",
        "role",
        "box_norm",
        "z_index",
        "alignment",
        "padding_norm",
        "background",
        "border",
        "radius_norm",
        "overlap_policy",
        "required",
    }
)

_BINARY_FIELD_NAMES = frozenset(
    {"bytes", "data", "image", "image_bytes", "image_data", "payload", "raw"}
)


class LayoutBlueprintValidationError(ValueError):
    """Raised when a blueprint cannot safely enter the production path."""


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LayoutBlueprintValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _reject_image_bytes(value: Any, path: str = "blueprint") -> None:
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise LayoutBlueprintValidationError(f"{path} must not contain binary image data")
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            if key_text.lower() in _BINARY_FIELD_NAMES and isinstance(
                child, (bytes, bytearray, memoryview)
            ):
                raise LayoutBlueprintValidationError(
                    f"{path}.{key_text} must not contain image bytes"
                )
            _reject_image_bytes(child, f"{path}.{key_text}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _reject_image_bytes(child, f"{path}[{index}]")


def _validate_box(box: Any, field: str) -> list[float]:
    if (
        not isinstance(box, Sequence)
        or isinstance(box, (str, bytes, bytearray))
        or len(box) != 4
        or not all(_is_number(item) for item in box)
    ):
        raise LayoutBlueprintValidationError(
            f"{field} must be [x, y, width, height] numbers"
        )
    x, y, width, height = (float(item) for item in box)
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise LayoutBlueprintValidationError(f"{field} has invalid normalized dimensions")
    if x > 1 or y > 1 or width > 1 or height > 1:
        raise LayoutBlueprintValidationError(f"{field} values must be within 0..1")
    if x + width > 1.0 + 1e-9 or y + height > 1.0 + 1e-9:
        raise LayoutBlueprintValidationError(f"{field} exceeds canvas bounds")
    return [x, y, width, height]


def _validate_padding(value: Any, field: str) -> float | list[float]:
    if _is_number(value):
        normalized = float(value)
        if 0 <= normalized <= 1:
            return normalized
    elif (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes, bytearray))
        and len(value) in {2, 4}
        and all(_is_number(item) and 0 <= float(item) <= 1 for item in value)
    ):
        return [float(item) for item in value]
    raise LayoutBlueprintValidationError(
        f"{field} must be a normalized number or a 2/4-value normalized list"
    )


def _geometry_payload(blueprint: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "blueprint_id": blueprint.get("blueprint_id"),
        "blueprint_version": blueprint.get("blueprint_version"),
        "canvas": blueprint.get("canvas"),
        "layout_family": blueprint.get("layout_family"),
        "regions": blueprint.get("regions"),
        "style_tokens": blueprint.get("style_tokens"),
        "fit_constraints": blueprint.get("fit_constraints"),
        "provenance": blueprint.get("provenance"),
    }


def compute_geometry_hash(blueprint: Mapping[str, Any]) -> str:
    """Return a deterministic SHA-256 for the complete content-free contract."""

    if not isinstance(blueprint, Mapping):
        raise LayoutBlueprintValidationError("blueprint must be an object")
    _reject_image_bytes(blueprint)
    try:
        canonical = json.dumps(
            _geometry_payload(blueprint),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise LayoutBlueprintValidationError(
            f"blueprint is not canonical JSON: {exc}"
        ) from exc
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_layout_blueprint(blueprint: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a detached normalized blueprint.

    Any missing, unsupported, out-of-bounds, or hash-mismatched value fails closed.
    """

    if not isinstance(blueprint, Mapping):
        raise LayoutBlueprintValidationError("blueprint must be an object")
    missing = BLUEPRINT_REQUIRED_FIELDS.difference(blueprint)
    if missing:
        raise LayoutBlueprintValidationError(
            f"blueprint missing required fields: {', '.join(sorted(missing))}"
        )
    _reject_image_bytes(blueprint)
    normalized = copy.deepcopy(dict(blueprint))
    normalized["blueprint_id"] = _require_nonempty_string(
        normalized["blueprint_id"], "blueprint_id"
    )
    version = normalized["blueprint_version"]
    if (
        isinstance(version, bool)
        or not isinstance(version, (str, int))
        or (isinstance(version, str) and not version.strip())
        or (isinstance(version, int) and version < 1)
    ):
        raise LayoutBlueprintValidationError(
            "blueprint_version must be a non-empty string or positive integer"
        )
    normalized["layout_family"] = _require_nonempty_string(
        normalized["layout_family"], "layout_family"
    )

    canvas = normalized["canvas"]
    if not isinstance(canvas, Mapping):
        raise LayoutBlueprintValidationError("canvas must be an object")
    if set(canvas) != {"width", "height"}:
        raise LayoutBlueprintValidationError("canvas must contain only width and height")
    if not _is_number(canvas["width"]) or float(canvas["width"]) <= 0:
        raise LayoutBlueprintValidationError("canvas.width must be positive")
    if not _is_number(canvas["height"]) or float(canvas["height"]) <= 0:
        raise LayoutBlueprintValidationError("canvas.height must be positive")

    for field in ("style_tokens", "fit_constraints", "provenance"):
        if not isinstance(normalized[field], Mapping):
            raise LayoutBlueprintValidationError(f"{field} must be an object")

    required_roles = normalized["fit_constraints"].get("required_roles")
    if (
        not isinstance(required_roles, Sequence)
        or isinstance(required_roles, (str, bytes, bytearray))
        or not required_roles
    ):
        raise LayoutBlueprintValidationError(
            "fit_constraints.required_roles must be a non-empty list"
        )
    normalized_required_roles: list[str] = []
    for role in required_roles:
        role_text = _require_nonempty_string(role, "required_roles item")
        if role_text not in SUPPORTED_REGION_ROLES:
            raise LayoutBlueprintValidationError(f"unsupported required role: {role_text}")
        if role_text not in normalized_required_roles:
            normalized_required_roles.append(role_text)
    normalized["fit_constraints"] = dict(normalized["fit_constraints"])
    normalized["fit_constraints"]["required_roles"] = normalized_required_roles

    regions = normalized["regions"]
    if (
        not isinstance(regions, Sequence)
        or isinstance(regions, (str, bytes, bytearray))
        or not regions
    ):
        raise LayoutBlueprintValidationError("regions must be a non-empty list")
    region_ids: set[str] = set()
    required_region_roles: set[str] = set()
    normalized_regions: list[dict[str, Any]] = []
    for index, raw_region in enumerate(regions):
        field = f"regions[{index}]"
        if not isinstance(raw_region, Mapping):
            raise LayoutBlueprintValidationError(f"{field} must be an object")
        missing_region = REGION_REQUIRED_FIELDS.difference(raw_region)
        if missing_region:
            raise LayoutBlueprintValidationError(
                f"{field} missing required fields: {', '.join(sorted(missing_region))}"
            )
        region = copy.deepcopy(dict(raw_region))
        region_id = _require_nonempty_string(region["region_id"], f"{field}.region_id")
        if region_id in region_ids:
            raise LayoutBlueprintValidationError(f"duplicate region_id: {region_id}")
        region_ids.add(region_id)
        region["region_id"] = region_id
        role = _require_nonempty_string(region["role"], f"{field}.role")
        if role not in SUPPORTED_REGION_ROLES:
            raise LayoutBlueprintValidationError(f"unsupported region role: {role}")
        region["role"] = role
        region["box_norm"] = _validate_box(region["box_norm"], f"{field}.box_norm")
        if not isinstance(region["z_index"], int) or isinstance(region["z_index"], bool):
            raise LayoutBlueprintValidationError(f"{field}.z_index must be an integer")
        region["alignment"] = _require_nonempty_string(
            region["alignment"], f"{field}.alignment"
        )
        region["padding_norm"] = _validate_padding(
            region["padding_norm"], f"{field}.padding_norm"
        )
        if not isinstance(region["radius_norm"], (int, float)) or isinstance(
            region["radius_norm"], bool
        ):
            raise LayoutBlueprintValidationError(f"{field}.radius_norm must be numeric")
        if not 0 <= float(region["radius_norm"]) <= 1:
            raise LayoutBlueprintValidationError(
                f"{field}.radius_norm must be within 0..1"
            )
        region["radius_norm"] = float(region["radius_norm"])
        region["overlap_policy"] = _require_nonempty_string(
            region["overlap_policy"], f"{field}.overlap_policy"
        )
        if not isinstance(region["required"], bool):
            raise LayoutBlueprintValidationError(f"{field}.required must be boolean")
        if region["required"]:
            required_region_roles.add(role)
        normalized_regions.append(region)
    normalized["regions"] = normalized_regions

    absent_required_roles = set(normalized_required_roles).difference(
        required_region_roles
    )
    if absent_required_roles:
        raise LayoutBlueprintValidationError(
            "required roles lack required regions: "
            + ", ".join(sorted(absent_required_roles))
        )

    supplied_hash = _require_nonempty_string(
        normalized["geometry_hash"], "geometry_hash"
    )
    expected_hash = compute_geometry_hash(normalized)
    if supplied_hash != expected_hash:
        raise LayoutBlueprintValidationError(
            f"geometry_hash mismatch: expected {expected_hash}"
        )
    normalized["geometry_hash"] = supplied_hash
    return normalized


def with_geometry_hash(blueprint: Mapping[str, Any]) -> dict[str, Any]:
    """Return a detached blueprint with its deterministic hash populated."""

    if not isinstance(blueprint, Mapping):
        raise LayoutBlueprintValidationError("blueprint must be an object")
    result = copy.deepcopy(dict(blueprint))
    result["geometry_hash"] = compute_geometry_hash(result)
    return result
