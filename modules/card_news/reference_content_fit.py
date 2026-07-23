"""Fail-closed content-fit checks for reference-driven card-news blueprints."""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


FIT_OUTCOMES = (
    "fit",
    "select_alternative_reference",
    "split_content_into_additional_slide",
    "reduce_nonessential_copy",
    "blocked",
)

MEDIA_ROLES = {"primary_media", "secondary_media"}
TEXT_ROLES = {
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
}


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _text_value(value: Any) -> str:
    if isinstance(value, Mapping):
        value = value.get("text", "")
    return str(value or "").strip()


def _positive_number(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) and number > 0 else None


class ReferenceContentFitChecker:
    """Evaluate whether one slide can occupy one immutable layout blueprint.

    The checker never mutates geometry, drops content, or shrinks typography.
    It returns a data-state outcome so the outer workflow can remain
    fallback-first while production itself fails closed.
    """

    def evaluate(
        self,
        blueprint: Mapping[str, Any],
        content: Optional[Mapping[str, Any]] = None,
        media: Optional[Any] = None,
        *,
        slide_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        blueprint = _as_mapping(blueprint)
        content_map = _as_mapping(content)
        regions = _as_sequence(blueprint.get("regions"))
        fit_constraints = _as_mapping(blueprint.get("fit_constraints"))
        checks: List[Dict[str, Any]] = []
        reasons: List[Dict[str, Any]] = []

        geometry_errors = self._validate_regions(regions)
        checks.append(
            {
                "check": "normalized_regions",
                "passed": not geometry_errors,
                "details": deepcopy(geometry_errors),
            }
        )
        for error in geometry_errors:
            reasons.append({"code": "invalid_geometry", **error})

        safe_area_errors = self._validate_safe_area(
            blueprint=blueprint,
            regions=regions,
            fit_constraints=fit_constraints,
        )
        checks.append(
            {
                "check": "mobile_safe_area",
                "passed": not safe_area_errors,
                "details": deepcopy(safe_area_errors),
            }
        )
        for error in safe_area_errors:
            reasons.append({"code": "mobile_safe_area_violation", **error})

        required_binding_errors = self._required_binding_errors(
            regions=regions,
            content=content_map,
            media=media,
        )
        checks.append(
            {
                "check": "required_role_binding",
                "passed": not required_binding_errors,
                "details": deepcopy(required_binding_errors),
            }
        )
        for error in required_binding_errors:
            reasons.append({"code": "missing_required_binding", **error})

        source_label_required = bool(
            fit_constraints.get("source_label_required")
            or any(
                _as_mapping(region).get("role") == "source_label"
                and _as_mapping(region).get("required")
                for region in regions
            )
        )
        source_label_present = bool(_text_value(content_map.get("source_label")))
        source_label_passed = not source_label_required or source_label_present
        checks.append(
            {
                "check": "source_label",
                "passed": source_label_passed,
                "required": source_label_required,
            }
        )
        if not source_label_passed:
            reasons.append(
                {
                    "code": "source_label_missing",
                    "role": "source_label",
                }
            )

        role_match = self._slide_role_matches(
            slide_role=slide_role,
            blueprint=blueprint,
            fit_constraints=fit_constraints,
        )
        checks.append({"check": "slide_role", "passed": role_match})
        if not role_match:
            reasons.append(
                {
                    "code": "slide_role_incompatible",
                    "slide_role": slide_role,
                }
            )

        media_errors = self._media_fit_errors(
            blueprint=blueprint,
            regions=regions,
            media=media,
        )
        checks.append(
            {
                "check": "media_fit",
                "passed": not media_errors,
                "details": deepcopy(media_errors),
            }
        )
        for error in media_errors:
            reasons.append({"code": "media_fit_failed", **error})

        copy_results = self._copy_fit_results(
            regions=regions,
            content=content_map,
            fit_constraints=fit_constraints,
        )
        checks.extend(copy_results["checks"])
        reasons.extend(copy_results["reasons"])

        outcome = self._resolve_outcome(
            geometry_errors=geometry_errors,
            safe_area_errors=safe_area_errors,
            required_binding_errors=required_binding_errors,
            source_label_passed=source_label_passed,
            role_match=role_match,
            media_errors=media_errors,
            headline_outcome=copy_results["headline_outcome"],
            body_outcome=copy_results["body_outcome"],
        )

        return {
            "status": "passed" if outcome == "fit" else "failed",
            "outcome": outcome,
            "fit": outcome == "fit",
            "reference_id": blueprint.get("reference_id"),
            "blueprint_id": blueprint.get("blueprint_id"),
            "blueprint_version": blueprint.get("blueprint_version"),
            "geometry_hash": blueprint.get("geometry_hash"),
            "checks": checks,
            "reasons": reasons,
        }

    @staticmethod
    def _validate_regions(regions: Sequence[Any]) -> List[Dict[str, Any]]:
        errors: List[Dict[str, Any]] = []
        if not regions:
            return [{"reason": "regions_missing"}]
        seen_ids = set()
        for index, raw_region in enumerate(regions):
            region = _as_mapping(raw_region)
            region_id = region.get("region_id")
            role = region.get("role")
            box = _as_sequence(region.get("box_norm"))
            if not region_id or not role:
                errors.append(
                    {
                        "region_index": index,
                        "region_id": region_id,
                        "reason": "region_id_or_role_missing",
                    }
                )
                continue
            if region_id in seen_ids:
                errors.append(
                    {
                        "region_index": index,
                        "region_id": region_id,
                        "reason": "duplicate_region_id",
                    }
                )
            seen_ids.add(region_id)
            if len(box) != 4:
                errors.append(
                    {
                        "region_index": index,
                        "region_id": region_id,
                        "reason": "box_norm_must_have_four_values",
                    }
                )
                continue
            try:
                x, y, width, height = (float(value) for value in box)
            except (TypeError, ValueError):
                errors.append(
                    {
                        "region_index": index,
                        "region_id": region_id,
                        "reason": "box_norm_non_numeric",
                    }
                )
                continue
            if not all(isfinite(value) for value in (x, y, width, height)):
                errors.append(
                    {
                        "region_index": index,
                        "region_id": region_id,
                        "reason": "box_norm_non_finite",
                    }
                )
            elif (
                x < 0
                or y < 0
                or width <= 0
                or height <= 0
                or x + width > 1
                or y + height > 1
            ):
                errors.append(
                    {
                        "region_index": index,
                        "region_id": region_id,
                        "reason": "box_norm_out_of_bounds",
                    }
                )
        return errors

    @staticmethod
    def _safe_area(
        blueprint: Mapping[str, Any],
        fit_constraints: Mapping[str, Any],
    ) -> Tuple[float, float, float, float]:
        raw = (
            fit_constraints.get("mobile_safe_area_norm")
            or _as_mapping(blueprint.get("canvas")).get("mobile_safe_area_norm")
            or (0.0, 0.0, 0.0, 0.0)
        )
        if isinstance(raw, Mapping):
            return (
                float(raw.get("left", 0)),
                float(raw.get("top", 0)),
                float(raw.get("right", 0)),
                float(raw.get("bottom", 0)),
            )
        values = _as_sequence(raw)
        if len(values) != 4:
            return (0.0, 0.0, 0.0, 0.0)
        try:
            return tuple(float(value) for value in values)  # type: ignore[return-value]
        except (TypeError, ValueError):
            return (0.0, 0.0, 0.0, 0.0)

    def _validate_safe_area(
        self,
        *,
        blueprint: Mapping[str, Any],
        regions: Sequence[Any],
        fit_constraints: Mapping[str, Any],
    ) -> List[Dict[str, Any]]:
        left, top, right, bottom = self._safe_area(blueprint, fit_constraints)
        boundary_epsilon = 1e-9
        errors: List[Dict[str, Any]] = []
        for raw_region in regions:
            region = _as_mapping(raw_region)
            if region.get("safe_area_exempt") or region.get("role") == "accent":
                continue
            box = _as_sequence(region.get("box_norm"))
            if len(box) != 4:
                continue
            try:
                x, y, width, height = (float(value) for value in box)
            except (TypeError, ValueError):
                continue
            if (
                x < left - boundary_epsilon
                or y < top - boundary_epsilon
                or x + width > 1 - right + boundary_epsilon
                or y + height > 1 - bottom + boundary_epsilon
            ):
                errors.append(
                    {
                        "region_id": region.get("region_id"),
                        "reason": "region_outside_mobile_safe_area",
                    }
                )
        return errors

    @staticmethod
    def _media_by_role(media: Any) -> Dict[str, List[Mapping[str, Any]]]:
        result: Dict[str, List[Mapping[str, Any]]] = {
            "primary_media": [],
            "secondary_media": [],
        }
        if isinstance(media, Mapping):
            for role in MEDIA_ROLES:
                value = media.get(role)
                if isinstance(value, Mapping):
                    result[role] = [value]
                else:
                    result[role] = [
                        item for item in _as_sequence(value) if isinstance(item, Mapping)
                    ]
            if not any(result.values()) and media:
                role = str(media.get("role") or "primary_media")
                result.setdefault(role, []).append(media)
        else:
            for item in _as_sequence(media):
                if not isinstance(item, Mapping):
                    continue
                role = str(item.get("role") or "primary_media")
                result.setdefault(role, []).append(item)
        return result

    def _required_binding_errors(
        self,
        *,
        regions: Sequence[Any],
        content: Mapping[str, Any],
        media: Any,
    ) -> List[Dict[str, Any]]:
        errors: List[Dict[str, Any]] = []
        media_by_role = self._media_by_role(media)
        for raw_region in regions:
            region = _as_mapping(raw_region)
            if not region.get("required"):
                continue
            role = str(region.get("role") or "")
            if role in MEDIA_ROLES:
                present = bool(media_by_role.get(role))
            elif role == "accent":
                present = True
            else:
                present = bool(_text_value(content.get(role)))
            if not present:
                errors.append(
                    {
                        "region_id": region.get("region_id"),
                        "role": role,
                        "reason": "required_region_has_no_binding",
                    }
                )
        return errors

    @staticmethod
    def _slide_role_matches(
        *,
        slide_role: Optional[str],
        blueprint: Mapping[str, Any],
        fit_constraints: Mapping[str, Any],
    ) -> bool:
        allowed = (
            fit_constraints.get("slide_role_fit")
            or fit_constraints.get("allowed_slide_roles")
            or blueprint.get("slide_role_fit")
        )
        if not slide_role or not allowed:
            return True
        allowed_values = {str(value) for value in _as_sequence(allowed)}
        if isinstance(allowed, str):
            allowed_values = {allowed}
        return slide_role in allowed_values

    def _media_fit_errors(
        self,
        *,
        blueprint: Mapping[str, Any],
        regions: Sequence[Any],
        media: Any,
    ) -> List[Dict[str, Any]]:
        requirements = _as_mapping(blueprint.get("media_requirements"))
        media_by_role = self._media_by_role(media)
        errors: List[Dict[str, Any]] = []
        canvas = _as_mapping(blueprint.get("canvas"))
        canvas_width = _positive_number(canvas.get("width")) or 1.0
        canvas_height = _positive_number(canvas.get("height")) or 1.0

        for role in MEDIA_ROLES:
            role_regions = [
                _as_mapping(region)
                for region in regions
                if _as_mapping(region).get("role") == role
            ]
            role_requirement = _as_mapping(requirements.get(role))
            assets = media_by_role.get(role, [])
            required_count = int(
                role_requirement.get(
                    "min_count",
                    sum(1 for region in role_regions if region.get("required")),
                )
                or 0
            )
            max_count_raw = role_requirement.get("max_count")
            max_count = int(max_count_raw) if max_count_raw is not None else len(role_regions)
            if len(assets) < required_count:
                errors.append(
                    {
                        "role": role,
                        "reason": "media_count_below_minimum",
                        "required": required_count,
                        "actual": len(assets),
                    }
                )
            if max_count >= 0 and len(assets) > max_count:
                errors.append(
                    {
                        "role": role,
                        "reason": "media_count_above_maximum",
                        "maximum": max_count,
                        "actual": len(assets),
                    }
                )

            tolerance = float(role_requirement.get("aspect_tolerance", 0.18))
            required_aspect = _positive_number(role_requirement.get("aspect_ratio"))
            for index, asset in enumerate(assets[: len(role_regions)]):
                asset_aspect = _positive_number(asset.get("aspect_ratio"))
                if asset_aspect is None:
                    width = _positive_number(asset.get("width"))
                    height = _positive_number(asset.get("height"))
                    asset_aspect = width / height if width and height else None
                region_aspect = required_aspect
                if region_aspect is None and index < len(role_regions):
                    box = _as_sequence(role_regions[index].get("box_norm"))
                    if len(box) == 4:
                        try:
                            region_aspect = (
                                float(box[2]) * canvas_width
                            ) / (float(box[3]) * canvas_height)
                        except (TypeError, ValueError, ZeroDivisionError):
                            region_aspect = None
                if asset_aspect and region_aspect:
                    relative_delta = abs(asset_aspect - region_aspect) / region_aspect
                    if relative_delta > tolerance and not asset.get("crop_allowed", False):
                        errors.append(
                            {
                                "role": role,
                                "asset_index": index,
                                "reason": "media_aspect_incompatible",
                                "required_aspect": round(region_aspect, 6),
                                "actual_aspect": round(asset_aspect, 6),
                            }
                        )
        return errors

    @staticmethod
    def _role_constraints(
        fit_constraints: Mapping[str, Any],
        role: str,
    ) -> Mapping[str, Any]:
        direct = _as_mapping(fit_constraints.get(role))
        if direct:
            return direct
        return _as_mapping(_as_mapping(fit_constraints.get("copy")).get(role))

    def _copy_fit_results(
        self,
        *,
        regions: Sequence[Any],
        content: Mapping[str, Any],
        fit_constraints: Mapping[str, Any],
    ) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []
        reasons: List[Dict[str, Any]] = []
        outcomes: Dict[str, str] = {"headline": "fit", "body": "fit"}
        region_by_role = {
            str(_as_mapping(region).get("role")): _as_mapping(region) for region in regions
        }

        for role in ("headline", "body"):
            text = _text_value(content.get(role))
            constraints = self._role_constraints(fit_constraints, role)
            region = region_by_role.get(role, {})
            max_chars = int(
                constraints.get("max_chars")
                or region.get("max_chars")
                or (48 if role == "headline" else 220)
            )
            max_lines = int(
                constraints.get("max_lines")
                or region.get("max_lines")
                or (3 if role == "headline" else 8)
            )
            chars_per_line = int(
                constraints.get("chars_per_line")
                or region.get("chars_per_line")
                or max(1, max_chars // max_lines)
            )
            explicit_lines = content.get(f"{role}_line_count")
            if explicit_lines is None and isinstance(content.get(role), Mapping):
                explicit_lines = _as_mapping(content.get(role)).get("line_count")
            estimated_lines = (
                int(explicit_lines)
                if explicit_lines is not None
                else max(1, (len(text) + chars_per_line - 1) // chars_per_line)
                if text
                else 0
            )
            character_occupancy = len(text) / max(max_chars, 1)
            line_occupancy = estimated_lines / max(max_lines, 1)
            occupancy = max(character_occupancy, line_occupancy)
            passed = occupancy <= 1.0
            if not passed:
                decision_occupancy = (
                    occupancy if explicit_lines is not None else character_occupancy
                )
                if role == "headline":
                    outcome = (
                        "reduce_nonessential_copy"
                        if decision_occupancy
                        <= float(constraints.get("reduction_limit", 1.25))
                        else "select_alternative_reference"
                    )
                else:
                    outcome = (
                        "reduce_nonessential_copy"
                        if decision_occupancy
                        <= float(constraints.get("reduction_limit", 1.25))
                        else "split_content_into_additional_slide"
                    )
                outcomes[role] = outcome
                reasons.append(
                    {
                        "code": f"{role}_occupancy_exceeded",
                        "role": role,
                        "occupancy": round(occupancy, 4),
                        "recommended_outcome": outcome,
                    }
                )
            checks.append(
                {
                    "check": f"{role}_occupancy",
                    "passed": passed,
                    "characters": len(text),
                    "estimated_lines": estimated_lines,
                    "max_characters": max_chars,
                    "max_lines": max_lines,
                    "occupancy": round(occupancy, 4),
                }
            )

        return {
            "checks": checks,
            "reasons": reasons,
            "headline_outcome": outcomes["headline"],
            "body_outcome": outcomes["body"],
        }

    @staticmethod
    def _resolve_outcome(
        *,
        geometry_errors: Sequence[Any],
        safe_area_errors: Sequence[Any],
        required_binding_errors: Sequence[Any],
        source_label_passed: bool,
        role_match: bool,
        media_errors: Sequence[Any],
        headline_outcome: str,
        body_outcome: str,
    ) -> str:
        if (
            geometry_errors
            or safe_area_errors
            or required_binding_errors
            or not source_label_passed
        ):
            return "blocked"
        if not role_match or media_errors or headline_outcome == "select_alternative_reference":
            return "select_alternative_reference"
        if body_outcome == "split_content_into_additional_slide":
            return "split_content_into_additional_slide"
        if (
            headline_outcome == "reduce_nonessential_copy"
            or body_outcome == "reduce_nonessential_copy"
        ):
            return "reduce_nonessential_copy"
        return "fit"


ReferenceContentFit = ReferenceContentFitChecker


def evaluate_reference_content_fit(
    blueprint: Mapping[str, Any],
    content: Optional[Mapping[str, Any]] = None,
    media: Optional[Any] = None,
    *,
    slide_role: Optional[str] = None,
) -> Dict[str, Any]:
    """Functional entry point for callers that do not retain a checker."""

    return ReferenceContentFitChecker().evaluate(
        blueprint,
        content,
        media,
        slide_role=slide_role,
    )
