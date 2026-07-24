"""Fail-closed visual gate for reference geometry drafts.

This module only evaluates a draft.  A passing result is not production
approval and deliberately does not expose a ``production_selectable`` field.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


SCHEMA_VERSION = "reference_geometry_visual_gate.v1"

_CAROUSEL_BADGE_RE = re.compile(r"(?<!\d)(\d{1,3})\s*/\s*(\d{1,3})(?!\d)")
_HANDLE_RE = re.compile(r"(?<![\w.])@[A-Za-z0-9._]{2,30}\b")
_PAGE_LABEL_RE = re.compile(
    r"(?<!\d)(?:page\s*)?(\d{1,3})\s*(?:of|/)\s*(\d{1,3})(?!\d)",
    re.IGNORECASE,
)
_INSTAGRAM_UI_TERMS = (
    "instagram",
    "팔로우",
    "팔로잉",
    "좋아요",
    "댓글 달기",
    "메시지 보내기",
    "공유하기",
    "스토리",
    "릴스",
    "sponsored",
    "follow",
    "following",
    "send message",
    "view insights",
    "add a comment",
)
_PROMPT_MARKERS = (
    "prompt:",
    "negative prompt",
    "generate an image",
    "create an image",
    "camera angle",
    "aspect ratio",
    "lighting:",
    "composition:",
    "style:",
    "이미지를 생성",
    "이미지 생성",
    "프롬프트",
    "카메라 앵글",
    "조명:",
    "구도:",
    "스타일:",
)


def _diagnostic(
    code: str,
    *,
    blocked: bool,
    detail: str,
    evidence: Any = None,
) -> Dict[str, Any]:
    result = {
        "code": code,
        "severity": "error" if blocked else "info",
        "blocked": blocked,
        "detail": detail,
    }
    if evidence is not None:
        result["evidence"] = evidence
    return result


def _recognized_text(draft: Mapping[str, Any]) -> List[str]:
    value = draft.get("recognized_text")
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        result = []
        for item in value:
            if isinstance(item, Mapping):
                text = str(item.get("text") or "").strip()
            else:
                text = str(item or "").strip()
            if text:
                result.append(text)
        return result
    return []


def _text_regions(draft: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    for key in ("text_regions", "text_boxes", "geometry_regions", "regions"):
        value = draft.get(key)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return [item for item in value if isinstance(item, Mapping)]
    return []


def _headline_regions(draft: Mapping[str, Any]) -> List[Dict[str, Any]]:
    regions = []
    for item in _text_regions(draft):
        role = str(
            item.get("role")
            or item.get("semantic_role")
            or item.get("type")
            or ""
        ).strip().casefold()
        if role in {"headline", "title", "hook_headline"}:
            regions.append(dict(item))
    if regions:
        return regions

    headline = draft.get("headline")
    if isinstance(headline, str) and headline.strip():
        box = draft.get("headline_box") or draft.get("headline_bbox")
        return [{"role": "headline", "text": headline.strip(), "box": box}]
    if isinstance(headline, Sequence) and not isinstance(headline, (str, bytes)):
        return [
            {"role": "headline", "text": str(item).strip(), "box": None}
            for item in headline
            if str(item or "").strip()
        ]
    return []


def _headline_text(region: Mapping[str, Any]) -> str:
    return str(
        region.get("text")
        or region.get("recognized_text")
        or region.get("content")
        or ""
    ).strip()


def _box(region: Mapping[str, Any]) -> Any:
    return (
        region.get("box")
        or region.get("bbox")
        or region.get("bounds")
        or region.get("geometry")
    )


def _canvas_size(draft: Mapping[str, Any]) -> Tuple[float, float] | None:
    canvas = draft.get("canvas") or draft.get("canvas_size") or {}
    if not isinstance(canvas, Mapping):
        return None
    try:
        width = float(canvas.get("width"))
        height = float(canvas.get("height"))
    except (TypeError, ValueError):
        return None
    if width <= 0 or height <= 0:
        return None
    return width, height


def _box_values(value: Any) -> Tuple[float, float, float, float] | None:
    if isinstance(value, Mapping):
        raw = (
            value.get("x"),
            value.get("y"),
            value.get("width", value.get("w")),
            value.get("height", value.get("h")),
        )
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if len(value) != 4:
            return None
        raw = tuple(value)
    else:
        return None
    try:
        x, y, width, height = (float(item) for item in raw)
    except (TypeError, ValueError):
        return None
    return x, y, width, height


def _normalized_box(
    value: Any,
    canvas_size: Tuple[float, float] | None,
) -> Tuple[float, float, float, float] | None:
    values = _box_values(value)
    if values is None:
        return None
    x, y, width, height = values
    if max(abs(x), abs(y), abs(width), abs(height)) <= 1.5:
        return values
    if canvas_size is None:
        return None
    canvas_width, canvas_height = canvas_size
    return (
        x / canvas_width,
        y / canvas_height,
        width / canvas_width,
        height / canvas_height,
    )


def _valid_crop_provenance(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    source = str(
        value.get("source_asset_id")
        or value.get("source_image_id")
        or value.get("source_path")
        or ""
    ).strip()
    crop = value.get("crop_box") or value.get("crop_bounds")
    method = str(value.get("method") or value.get("operation") or "").strip()
    return bool(source and method and _box_values(crop) is not None)


def _prompt_paragraph_reason(text: str) -> str | None:
    normalized = " ".join(text.split())
    marker_count = sum(
        marker in normalized.casefold() for marker in _PROMPT_MARKERS
    )
    sentence_count = len(re.findall(r"[.!?。！？](?:\s|$)", normalized))
    if len(normalized) > 220:
        return "headline_exceeds_220_characters"
    if len(normalized) > 140 and (marker_count or sentence_count >= 3):
        return "headline_looks_like_prompt_paragraph"
    if marker_count >= 2:
        return "headline_contains_multiple_prompt_markers"
    return None


def evaluate_reference_geometry_draft(draft: Mapping[str, Any]) -> Dict[str, Any]:
    """Evaluate one geometry draft without granting production selection."""

    diagnostics: List[Dict[str, Any]] = []
    if not isinstance(draft, Mapping):
        diagnostics.append(
            _diagnostic(
                "draft_json_invalid",
                blocked=True,
                detail="Draft input must be a JSON object.",
            )
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "rework_required",
            "diagnostics": diagnostics,
        }

    if draft.get("geometry_contract_valid") is not True:
        diagnostics.append(
            _diagnostic(
                "geometry_contract_invalid",
                blocked=True,
                detail="geometry_contract_valid must be explicitly true.",
            )
        )

    if not _valid_crop_provenance(draft.get("crop_provenance")):
        diagnostics.append(
            _diagnostic(
                "crop_provenance_missing_or_incomplete",
                blocked=True,
                detail=(
                    "Crop provenance requires source identity, crop box, and crop method."
                ),
            )
        )

    recognized = _recognized_text(draft)
    combined_text = "\n".join(recognized)
    badge_matches = []
    for match in _CAROUSEL_BADGE_RE.finditer(combined_text):
        current, total = int(match.group(1)), int(match.group(2))
        if total > 1 and 0 < current <= total:
            badge_matches.append(match.group(0))
    if badge_matches:
        diagnostics.append(
            _diagnostic(
                "carousel_ui_badge_detected",
                blocked=True,
                detail="Recognized text contains an N/N carousel UI badge.",
                evidence=badge_matches,
            )
        )

    lowered = combined_text.casefold()
    ui_terms = sorted({term for term in _INSTAGRAM_UI_TERMS if term in lowered})
    handles = sorted(set(_HANDLE_RE.findall(combined_text)))
    page_labels = sorted(match.group(0) for match in _PAGE_LABEL_RE.finditer(combined_text))
    if ui_terms:
        diagnostics.append(
            _diagnostic(
                "instagram_ui_text_detected",
                blocked=True,
                detail="Recognized text contains explicit Instagram UI/header language.",
                evidence=ui_terms,
            )
        )
    if handles and not ui_terms:
        diagnostics.append(
            _diagnostic(
                "content_handle_present_not_blocked",
                blocked=False,
                detail=(
                    "An @handle may be editorial content; it is not treated as UI "
                    "without an explicit companion UI pattern."
                ),
                evidence=handles,
            )
        )
    if page_labels and not badge_matches:
        diagnostics.append(
            _diagnostic(
                "page_label_present_not_blocked",
                blocked=False,
                detail=(
                    "A page label alone may be content pagination; it is not treated "
                    "as carousel UI unless it matches the explicit N/N badge rule."
                ),
                evidence=page_labels,
            )
        )

    headlines = _headline_regions(draft)
    if not headlines:
        diagnostics.append(
            _diagnostic(
                "headline_missing",
                blocked=True,
                detail="Exactly one headline region is required.",
            )
        )
    elif len(headlines) > 1:
        diagnostics.append(
            _diagnostic(
                "headline_multiple",
                blocked=True,
                detail="Multiple headline regions were classified.",
                evidence={"count": len(headlines)},
            )
        )
    else:
        headline = headlines[0]
        headline_text = _headline_text(headline)
        if not headline_text:
            diagnostics.append(
                _diagnostic(
                    "headline_text_missing",
                    blocked=True,
                    detail="The headline region has no recognized headline text.",
                )
            )
        else:
            paragraph_reason = _prompt_paragraph_reason(headline_text)
            if paragraph_reason:
                diagnostics.append(
                    _diagnostic(
                        "headline_prompt_paragraph",
                        blocked=True,
                        detail=paragraph_reason,
                        evidence={"length": len(headline_text)},
                    )
                )

        normalized = _normalized_box(_box(headline), _canvas_size(draft))
        if normalized is None:
            diagnostics.append(
                _diagnostic(
                    "headline_box_missing_or_unscaled",
                    blocked=True,
                    detail=(
                        "Headline geometry requires a normalized box or pixel box "
                        "with a valid canvas size."
                    ),
                )
            )
        else:
            x, y, width, height = normalized
            in_canvas = (
                x >= 0
                and y >= 0
                and width > 0
                and height > 0
                and x + width <= 1.02
                and y + height <= 1.02
            )
            plausible_size = width >= 0.15 and 0.02 <= height <= 0.40
            plausible_position = y <= 0.80
            if not (in_canvas and plausible_size and plausible_position):
                diagnostics.append(
                    _diagnostic(
                        "headline_box_abnormal",
                        blocked=True,
                        detail=(
                            "Headline box is outside the canvas, implausibly sized, "
                            "or positioned below the usable headline area."
                        ),
                        evidence={
                            "x": round(x, 6),
                            "y": round(y, 6),
                            "width": round(width, 6),
                            "height": round(height, 6),
                        },
                    )
                )

    blocked = any(item["blocked"] for item in diagnostics)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "rework_required" if blocked else "pass",
        "diagnostics": diagnostics,
        "summary": {
            "blocking_count": sum(item["blocked"] for item in diagnostics),
            "informational_count": sum(not item["blocked"] for item in diagnostics),
            "recognized_text_count": len(recognized),
            "headline_count": len(headlines),
        },
    }


class ReferenceGeometryVisualGate:
    """Small object interface for pipeline dependency injection."""

    def evaluate(self, draft: Mapping[str, Any]) -> Dict[str, Any]:
        return evaluate_reference_geometry_draft(draft)


__all__ = [
    "ReferenceGeometryVisualGate",
    "SCHEMA_VERSION",
    "evaluate_reference_geometry_draft",
]
