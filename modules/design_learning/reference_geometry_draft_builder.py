"""Build unapproved Reference V2 geometry drafts from local owner images.

OCR boxes may define draft text geometry. Areas without OCR evidence are
recorded only as media/background candidates and never become production
bindings automatically.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from PIL import Image

from modules.design_learning.layout_blueprint_contract import (
    LayoutBlueprintValidationError,
    validate_layout_blueprint,
    with_geometry_hash,
)
from modules.design_learning.reference_specimen_registry import (
    extract_reference_draft_candidates,
)
from modules.tool_adapters.paddleocr_runtime import extract_korean_text


DRAFT_SCHEMA_VERSION = "owner_reference_v2_geometry_draft_v1"
DRAFT_INDEX_SCHEMA_VERSION = "owner_reference_v2_geometry_draft_index_v1"
GRID_DIVISIONS = 3
MIN_VIEWPORT_CONFIDENCE = 0.55
CROP_METHOD = (
    "instagram_full_width_4x5_alternate_edges_ui_avoidance_v2"
)
HEADER_UI_PATTERN = re.compile(
    r"(게시물|팔로우|원본\s*오디오|오리지널\s*오디오|original\s*audio|"
    r"music|음악|내\s*스토리|your\s*story)",
    re.IGNORECASE,
)
FOOTER_UI_PATTERN = re.compile(
    r"(좋아요|댓글|답글|공유|더\s*보기|조회|일\s*전|주\s*전|"
    r"\d{1,2}\s*월\s*\d{1,2}\s*일|comment|like|share|view)",
    re.IGNORECASE,
)
CAROUSEL_BADGE_PATTERN = re.compile(r"^\s*\d{1,2}\s*/\s*\d{1,2}\s*$")
ACCOUNT_UI_PATTERN = re.compile(
    r"^@?[a-z0-9][a-z0-9._]{2,30}$",
    re.IGNORECASE,
)
BRAND_OR_LABEL_PATTERN = re.compile(
    r"(^@|mktg\s*with\s*ai|원본|생성본|step\s*\d+|swipe|다음\s*페이지|"
    r"마지막\s*페이지|image\s*prompt)",
    re.IGNORECASE,
)
PROMPT_PARAGRAPH_PATTERN = re.compile(
    r"(image\s*prompt|reference\s*image|a\s+(close[- ]?up|dramatic|stylish)|"
    r"lighting|composition|aspect\s*ratio|cinematic|editorial|"
    r"프롬프트|가이드라인|svg\s*코드|업로드)",
    re.IGNORECASE,
)


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _receipt_value(receipt: Any, field: str, fallback: Any) -> Any:
    if isinstance(receipt, Mapping):
        return receipt.get(field, fallback)
    return getattr(receipt, field, fallback)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _box_from_polygon(value: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(value, Sequence) or isinstance(
        value, (str, bytes, bytearray)
    ):
        return None
    points: list[tuple[float, float]] = []
    for point in value:
        if (
            isinstance(point, Sequence)
            and not isinstance(point, (str, bytes, bytearray))
            and len(point) >= 2
        ):
            try:
                points.append((float(point[0]), float(point[1])))
            except (TypeError, ValueError):
                return None
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _pixel_box(value: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(value, Sequence) or isinstance(
        value, (str, bytes, bytearray)
    ):
        return None
    if len(value) == 4 and all(isinstance(item, (int, float)) for item in value):
        x1, y1, x2, y2 = (float(item) for item in value)
        return x1, y1, x2, y2
    return _box_from_polygon(value)


def _normalize_box(
    value: Any,
    *,
    width: int,
    height: int,
) -> list[float] | None:
    box = _pixel_box(value)
    if box is None:
        return None
    x1, y1, x2, y2 = box
    x1 = min(max(x1, 0.0), float(width))
    y1 = min(max(y1, 0.0), float(height))
    x2 = min(max(x2, 0.0), float(width))
    y2 = min(max(y2, 0.0), float(height))
    if x2 - x1 < 1 or y2 - y1 < 1:
        return None
    return [
        round(x1 / width, 6),
        round(y1 / height, 6),
        round((x2 - x1) / width, 6),
        round((y2 - y1) / height, 6),
    ]


def _ocr_observations(
    receipt: Any,
    *,
    width: int,
    height: int,
) -> list[dict[str, Any]]:
    lines = list(_receipt_value(receipt, "lines", ()))
    scores = list(_receipt_value(receipt, "scores", ()))
    boxes = list(_receipt_value(receipt, "boxes", ()))
    polygons = list(_receipt_value(receipt, "polys", ()))
    count = max(len(lines), len(boxes), len(polygons))
    observed: list[dict[str, Any]] = []
    for index in range(count):
        raw_box = boxes[index] if index < len(boxes) else None
        if raw_box is None and index < len(polygons):
            raw_box = polygons[index]
        pixel_box = _pixel_box(raw_box)
        normalized = _normalize_box(raw_box, width=width, height=height)
        if normalized is None or pixel_box is None:
            continue
        x1, y1, x2, y2 = pixel_box
        observed.append(
            {
                "line": str(lines[index]) if index < len(lines) else "",
                "score": float(scores[index]) if index < len(scores) else None,
                "box_norm": normalized,
                "box_px": [
                    max(0.0, min(float(width), x1)),
                    max(0.0, min(float(height), y1)),
                    max(0.0, min(float(width), x2)),
                    max(0.0, min(float(height), y2)),
                ],
                "area": normalized[2] * normalized[3],
            }
        )
    return observed


def _horizontal_transition_scores(image: Image.Image) -> list[float]:
    grayscale = image.convert("L").resize((64, image.height))
    get_pixels = getattr(grayscale, "get_flattened_data", grayscale.getdata)
    pixels = list(get_pixels())
    width = grayscale.width
    scores = [0.0] * grayscale.height
    for row in range(1, grayscale.height):
        start = row * width
        previous = start - width
        immediate = sum(
            abs(pixels[start + column] - pixels[previous + column])
            for column in range(width)
        ) / (width * 255.0)
        scores[row] = immediate
    return scores


def _full_screen_ui_kind(
    item: Mapping[str, Any],
    *,
    width: int,
    height: int,
) -> str | None:
    line = str(item.get("line") or "").strip()
    box = item.get("box_px")
    if (
        not line
        or not isinstance(box, Sequence)
        or len(box) != 4
    ):
        return None
    center_x = (float(box[0]) + float(box[2])) / 2.0
    center_y = (float(box[1]) + float(box[3])) / 2.0
    box_height = max(0.0, float(box[3]) - float(box[1]))
    if (
        CAROUSEL_BADGE_PATTERN.fullmatch(line)
        and center_x >= width * 0.72
        and box_height <= height * 0.045
    ):
        return "carousel_badge"
    if (
        center_y <= height * 0.32
        and box_height <= max(height * 0.045, width * 0.18)
        and (
            HEADER_UI_PATTERN.search(line)
            or ACCOUNT_UI_PATTERN.fullmatch(line)
        )
    ):
        return "header_ui"
    if (
        center_y >= height * 0.50
        and box_height <= max(height * 0.055, width * 0.20)
        and FOOTER_UI_PATTERN.search(line)
    ):
        return "footer_ui"
    return None


def _ui_penalty(
    observations: Sequence[Mapping[str, Any]],
    *,
    top: int,
    bottom: int,
    width: int,
    height: int,
) -> tuple[float, list[str]]:
    penalty = 0.0
    included: list[str] = []
    for item in observations:
        line = str(item.get("line") or "").strip()
        box = item.get("box_px")
        if (
            not line
            or not isinstance(box, Sequence)
            or len(box) != 4
        ):
            continue
        center_y = (float(box[1]) + float(box[3])) / 2.0
        if center_y < top or center_y > bottom:
            continue
        kind = _full_screen_ui_kind(item, width=width, height=height)
        if kind == "carousel_badge":
            included.append(f"ignored_badge:{line[:80]}")
            continue
        relative_y = (center_y - top) / max(1.0, bottom - top)
        if kind == "header_ui" and relative_y <= 0.18:
            penalty += 0.34
            included.append(f"header:{line[:80]}")
        if kind == "footer_ui" and relative_y >= 0.82:
            penalty += 0.38
            included.append(f"footer:{line[:80]}")
    return min(1.0, penalty), included


def detect_instagram_content_viewport(
    image: Image.Image,
    full_screen_ocr_receipt: Any,
    *,
    minimum_confidence: float = MIN_VIEWPORT_CONFIDENCE,
) -> dict[str, Any]:
    """Select one full-width 4:5 window without a fixed y coordinate."""

    width, height = image.size
    crop_height = int(round(width * 5 / 4))
    if crop_height > height:
        return {
            "status": "failed",
            "reason_code": "image_shorter_than_full_width_4x5",
            "confidence": 0.0,
            "crop_method": CROP_METHOD,
        }
    observations = _ocr_observations(
        full_screen_ocr_receipt,
        width=width,
        height=height,
    )
    classified = [
        (
            item,
            _full_screen_ui_kind(item, width=width, height=height),
        )
        for item in observations
    ]
    header_bottoms = [
        float(item["box_px"][3])
        for item, kind in classified
        if kind == "header_ui"
    ]
    footer_tops = [
        float(item["box_px"][1])
        for item, kind in classified
        if kind == "footer_ui"
    ]
    header_bottom = max(header_bottoms) if header_bottoms else None
    footer_top = min(footer_tops) if footer_tops else None
    transitions = _horizontal_transition_scores(image)
    peak_radius = max(3, width // 240)
    local_peaks = [
        max(
            transitions[max(0, row - peak_radius): min(height, row + peak_radius + 1)],
            default=0.0,
        )
        for row in range(height)
    ]
    maximum_top = height - crop_height
    known_tops = {0, maximum_top}
    known_tops.update(
        int(round(value))
        for value in header_bottoms
        if 0 <= value <= maximum_top
    )
    known_tops.update(
        int(round(value - crop_height))
        for value in footer_tops
        if 0 <= value - crop_height <= maximum_top
    )
    candidates: list[dict[str, Any]] = []
    for top in range(maximum_top + 1):
        bottom = top + crop_height
        start_exact = transitions[top] if top < len(transitions) else 0.0
        end_exact = transitions[bottom] if bottom < len(transitions) else 0.0
        start_transition = max(
            start_exact,
            (local_peaks[top] if top < len(local_peaks) else 0.0) * 0.85,
        )
        end_transition = max(
            end_exact,
            (local_peaks[bottom] if bottom < len(local_peaks) else 0.0) * 0.85,
        )
        expanded_boundary_score = (
            max(start_transition, end_transition) * 0.58
            + min(start_transition, end_transition) * 0.42
        )
        exact_boundary_score = (
            max(start_exact, end_exact) * 0.58
            + min(start_exact, end_exact) * 0.42
        )
        boundary_score = (
            expanded_boundary_score * 0.70
            + exact_boundary_score * 0.30
        )
        ui_penalty, included_ui = _ui_penalty(
            observations,
            top=top,
            bottom=bottom,
            width=width,
            height=height,
        )
        header_anchor = 0.5
        if header_bottom is not None:
            if top >= header_bottom:
                header_anchor = max(0.0, 1.0 - (top - header_bottom) / (width * 0.3))
            else:
                header_anchor = max(0.0, 1.0 - (header_bottom - top) / (width * 0.1))
        footer_anchor = 0.5
        if footer_top is not None:
            if bottom <= footer_top:
                footer_anchor = max(0.0, 1.0 - (footer_top - bottom) / (width * 0.3))
            else:
                footer_anchor = max(0.0, 1.0 - (bottom - footer_top) / (width * 0.1))
        anchor_score = (header_anchor + footer_anchor) / 2.0
        nearest_known_edge = min(abs(top - value) for value in known_tops)
        known_edge_score = max(
            0.0,
            1.0 - nearest_known_edge / max(1.0, width * 0.12),
        )
        raw_score = (
            min(1.0, boundary_score / 0.10) * 0.47
            + min(1.0, exact_boundary_score / 0.10) * 0.08
            + (1.0 - ui_penalty) * 0.18
            + anchor_score * 0.17
            + known_edge_score * 0.10
        )
        candidates.append(
            {
                "top": top,
                "bottom": bottom,
                "raw_score": raw_score,
                "boundary_score": boundary_score,
                "start_transition": start_transition,
                "end_transition": end_transition,
                "exact_boundary_score": exact_boundary_score,
                "ui_penalty": ui_penalty,
                "included_ui": included_ui,
                "anchor_score": anchor_score,
                "known_edge_score": known_edge_score,
            }
        )
    ranked = sorted(
        candidates,
        key=lambda item: (
            -item["raw_score"],
            -item["boundary_score"],
            -item["exact_boundary_score"],
            item["ui_penalty"],
            item["top"],
        ),
    )
    best = ranked[0]
    separation = max(12, width // 100)
    alternative = next(
        (
            item
            for item in ranked[1:]
            if abs(item["top"] - best["top"]) >= separation
        ),
        ranked[1] if len(ranked) > 1 else best,
    )
    margin = max(0.0, best["raw_score"] - alternative["raw_score"])
    boundary_evidence = min(1.0, best["boundary_score"] / 0.08)
    paired_anchor_evidence = (
        min(1.0, best["anchor_score"] * 1.25)
        if header_bottom is not None and footer_top is not None
        else 0.0
    )
    confidence = min(
        1.0,
        best["raw_score"] * 0.88
        + boundary_evidence * 0.08
        + paired_anchor_evidence * boundary_evidence * 0.08
        + min(1.0, margin / 0.08) * 0.04,
    )
    status = "detected" if confidence >= minimum_confidence else "failed"
    return {
        "status": status,
        "reason_code": (
            "ok" if status == "detected" else "viewport_confidence_below_threshold"
        ),
        "confidence": round(confidence, 6),
        "minimum_confidence": minimum_confidence,
        "crop_box_original_px": {
            "x": 0,
            "y": int(best["top"]),
            "width": width,
            "height": crop_height,
        },
        "crop_method": CROP_METHOD,
        "score_components": {
            "raw_score": round(best["raw_score"], 6),
            "boundary_score": round(best["boundary_score"], 6),
            "start_transition": round(best["start_transition"], 6),
            "end_transition": round(best["end_transition"], 6),
            "ui_penalty": round(best["ui_penalty"], 6),
            "anchor_score": round(best["anchor_score"], 6),
            "known_edge_score": round(best["known_edge_score"], 6),
            "paired_anchor_evidence": round(paired_anchor_evidence, 6),
            "separated_runner_up_margin": round(margin, 6),
        },
        "ui_text_inside_selected_window": best["included_ui"],
        "header_anchor_bottom_px": header_bottom,
        "footer_anchor_top_px": footer_top,
        "candidate_window_count": len(candidates),
        "alternate_boundary_candidates": [
            {
                "y": int(item["top"]),
                "confidence_basis_score": round(item["raw_score"], 6),
                "boundary_score": round(item["boundary_score"], 6),
                "ui_penalty": round(item["ui_penalty"], 6),
            }
            for item in ranked[:5]
        ],
        "full_width_4x5": True,
    }


def _crop_ui_kind(item: Mapping[str, Any]) -> str | None:
    line = str(item.get("line") or "").strip()
    box = item.get("box_norm")
    if not line or not isinstance(box, Sequence) or len(box) != 4:
        return None
    x, y, width, height = (float(value) for value in box)
    center_x = x + width / 2.0
    if (
        CAROUSEL_BADGE_PATTERN.fullmatch(line)
        and center_x >= 0.72
        and y <= 0.18
    ):
        return "carousel_badge"
    if y <= 0.14 and (
        HEADER_UI_PATTERN.search(line)
        or line.casefold() in {"내 스토리", "your story"}
        or (ACCOUNT_UI_PATTERN.fullmatch(line) and width <= 0.45)
    ):
        return "story_or_account_header"
    if y + height >= 0.86 and (
        FOOTER_UI_PATTERN.search(line)
        or CAROUSEL_BADGE_PATTERN.fullmatch(line)
    ):
        return "carousel_or_footer_ui"
    return None


def _filter_crop_observations(
    observations: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    retained: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for item in observations:
        kind = _crop_ui_kind(item)
        if kind is None:
            retained.append(dict(item))
            continue
        excluded.append(
            {
                "recognized_text": str(item.get("line") or ""),
                "box_norm": copy.deepcopy(item.get("box_norm")),
                "reason": kind,
            }
        )
    return retained, excluded


def _is_prompt_paragraph(text: str) -> bool:
    compact = " ".join(text.split())
    ascii_letters = sum(character.isascii() and character.isalpha() for character in compact)
    letter_count = sum(character.isalpha() for character in compact)
    english_ratio = ascii_letters / letter_count if letter_count else 0.0
    return bool(
        PROMPT_PARAGRAPH_PATTERN.search(compact)
        or len(compact) >= 72
        or (len(compact) >= 34 and english_ratio >= 0.72)
    )


def _headline_classification(
    observations: Sequence[Mapping[str, Any]],
) -> tuple[int | None, list[dict[str, Any]]]:
    if not observations:
        return None, []
    heights = sorted(float(item["box_norm"][3]) for item in observations)
    median_height = heights[len(heights) // 2]
    scored: list[dict[str, Any]] = []
    for index, item in enumerate(observations):
        text = " ".join(str(item.get("line") or "").split())
        box = item["box_norm"]
        top = float(box[1])
        box_height = float(box[3])
        compact_length = len(text.replace(" ", ""))
        prompt_paragraph = _is_prompt_paragraph(text)
        brand_or_ui = bool(
            BRAND_OR_LABEL_PATTERN.search(text)
            or CAROUSEL_BADGE_PATTERN.fullmatch(text)
        )
        eligible = (
            bool(text)
            and not prompt_paragraph
            and not brand_or_ui
            and compact_length <= 52
        )
        top_score = max(0.0, 1.0 - top / 0.62)
        size_ratio = box_height / max(median_height, 0.001)
        size_score = min(1.0, size_ratio / 2.0)
        short_copy_score = (
            1.0
            if 4 <= compact_length <= 30
            else max(0.0, 1.0 - abs(compact_length - 22) / 40.0)
        )
        density_contrast = min(
            1.0,
            (box_height * max(float(box[2]), 0.05))
            / max(median_height * 0.35, 0.001),
        )
        score = (
            top_score * 0.34
            + size_score * 0.30
            + short_copy_score * 0.20
            + density_contrast * 0.16
        )
        scored.append(
            {
                "index": index,
                "score": round(score, 6),
                "eligible": eligible,
                "prompt_paragraph": prompt_paragraph,
                "brand_or_ui": brand_or_ui,
                "recognized_text": text,
            }
        )
    eligible_items = [item for item in scored if item["eligible"]]
    if not eligible_items:
        return None, scored
    best = max(
        eligible_items,
        key=lambda item: (item["score"], -item["index"]),
    )
    return (
        int(best["index"]) if float(best["score"]) >= 0.48 else None,
        scored,
    )


def _intersection_ratio(left: Sequence[float], right: Sequence[float]) -> float:
    lx, ly, lw, lh = (float(value) for value in left)
    rx, ry, rw, rh = (float(value) for value in right)
    x1, y1 = max(lx, rx), max(ly, ry)
    x2, y2 = min(lx + lw, rx + rw), min(ly + lh, ry + rh)
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area = max(0.0, lw) * max(0.0, lh)
    return intersection / area if area else 0.0


def _media_background_candidates(
    text_boxes: Sequence[Sequence[float]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    cell = 1.0 / GRID_DIVISIONS
    for row in range(GRID_DIVISIONS):
        for column in range(GRID_DIVISIONS):
            box = [
                round(column * cell, 6),
                round(row * cell, 6),
                round(cell, 6),
                round(cell, 6),
            ]
            maximum_overlap = max(
                (_intersection_ratio(box, text_box) for text_box in text_boxes),
                default=0.0,
            )
            if maximum_overlap > 0.05:
                continue
            candidates.append(
                {
                    "candidate_id": f"unobserved-grid-{row + 1}-{column + 1}",
                    "candidate_kind": "media_or_background_candidate",
                    "box_norm": box,
                    "detection_basis": "no_ocr_text_overlap_in_grid_cell",
                    "maximum_text_overlap_ratio": round(maximum_overlap, 6),
                    "classification_unverified": True,
                    "production_binding": False,
                }
            )
    return candidates


def _resolve_image_path(source_root: Path, source_relative_path: str) -> Path:
    relative = Path(source_relative_path)
    if relative.is_absolute() or relative.drive or ".." in relative.parts:
        raise ValueError("source_relative_path must remain relative")
    candidates = [source_root.parent / relative, source_root / relative]
    if relative.parts and relative.parts[0].casefold() == source_root.name.casefold():
        candidates.insert(0, source_root.parent / relative)
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


def build_reference_geometry_draft(
    candidate: Mapping[str, Any],
    *,
    source_root: str | Path,
    crop_output_dir: str | Path,
    ocr_extractor: Callable[..., Any] = extract_korean_text,
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    """Build one local-only, non-selectable geometry draft."""

    reference_id = str(candidate.get("reference_id") or "").strip()
    source_relative_path = str(candidate.get("source_relative_path") or "").strip()
    if not reference_id or not source_relative_path:
        raise ValueError("reference_id and source_relative_path are required")
    image_path = _resolve_image_path(Path(source_root), source_relative_path)
    before = image_path.stat()
    original_sha256 = _sha256_file(image_path)
    with Image.open(image_path) as image:
        full_image = image.convert("RGB")
        width, height = full_image.size
    full_receipt = ocr_extractor(image_path, timeout_seconds=timeout_seconds)
    viewport = detect_instagram_content_viewport(full_image, full_receipt)
    after = image_path.stat()
    source_unchanged = (before.st_size, before.st_mtime_ns) == (
        after.st_size,
        after.st_mtime_ns,
    )
    if not source_unchanged:
        raise RuntimeError("source image changed during geometry draft extraction")
    if viewport["status"] != "detected":
        return {
            "schema_version": DRAFT_SCHEMA_VERSION,
            "status": "draft_failed_low_viewport_confidence",
            "reference_id": reference_id,
            "source_relative_path": source_relative_path,
            "viewport_detection": viewport,
            "original_sha256": original_sha256,
            "crop_sha256": None,
            "approval_status": "draft_unapproved",
            "owner_approval_receipt_id": None,
            "reference_only": True,
            "production_selectable": False,
            "production_registry_written": False,
            "auto_approval_performed": False,
            "source_files_modified": False,
        }

    crop_box = viewport["crop_box_original_px"]
    left = int(crop_box["x"])
    top = int(crop_box["y"])
    crop_width = int(crop_box["width"])
    crop_height = int(crop_box["height"])
    cropped = full_image.crop(
        (left, top, left + crop_width, top + crop_height)
    )
    crop_dir = Path(crop_output_dir)
    crop_dir.mkdir(parents=True, exist_ok=True)
    crop_path = crop_dir / f"{reference_id}.png"
    cropped.save(crop_path, format="PNG")
    crop_sha256 = _sha256_file(crop_path)
    receipt = ocr_extractor(crop_path, timeout_seconds=timeout_seconds)
    if not bool(_receipt_value(receipt, "success", False)):
        return {
            "schema_version": DRAFT_SCHEMA_VERSION,
            "status": "draft_failed_crop_ocr",
            "reference_id": reference_id,
            "source_relative_path": source_relative_path,
            "viewport_detection": viewport,
            "crop_path": str(crop_path),
            "original_sha256": original_sha256,
            "crop_sha256": crop_sha256,
            "ocr_failure_reason": str(_receipt_value(receipt, "reason", "")),
            "approval_status": "draft_unapproved",
            "owner_approval_receipt_id": None,
            "reference_only": True,
            "production_selectable": False,
            "production_registry_written": False,
            "auto_approval_performed": False,
            "source_files_modified": False,
        }
    raw_observed = _ocr_observations(
        receipt,
        width=crop_width,
        height=crop_height,
    )
    observed, excluded_ui_regions = _filter_crop_observations(raw_observed)
    lines = list(_receipt_value(receipt, "lines", ()))

    headline_index, headline_scores = _headline_classification(observed)
    regions: list[dict[str, Any]] = []
    for index, item in enumerate(observed):
        role = "headline" if index == headline_index else "body"
        regions.append(
            {
                "region_id": f"ocr-text-{index + 1:03d}",
                "role": role,
                "box_norm": item["box_norm"],
                "z_index": 10 + index,
                "alignment": "left",
                "padding_norm": 0.0,
                "background": {
                    "status": "unmeasured_draft",
                    "production_token": False,
                },
                "border": {
                    "status": "unmeasured_draft",
                    "production_token": False,
                },
                "radius_norm": 0.0,
                "overlap_policy": "draft_observed_ocr_overlap_allowed",
                "required": role == "headline",
                "detection_source": "paddleocr_box",
                "role_assignment": (
                    "heuristic_headline_semantic_geometry_v2"
                    if role == "headline"
                    else "unverified_text_body"
                ),
                "recognized_text": item["line"],
                "ocr_confidence": item["score"],
            }
        )

    blueprint_id = str(
        candidate.get("suggested_blueprint_id")
        or f"bp-draft-{reference_id}"
    ).strip()
    blueprint = {
        "blueprint_id": blueprint_id,
        "blueprint_version": "draft-1",
        "canvas": {"width": crop_width, "height": crop_height},
        "layout_family": "ocr_observed_geometry_draft",
        "regions": regions,
        "style_tokens": {
            "status": "draft_unmeasured",
            "source": "ocr_geometry_only",
        },
        "fit_constraints": {
            "required_roles": ["headline"] if headline_index is not None else [],
            "status": "draft_pending_owner_approval",
        },
        "geometry_hash": "pending",
        "provenance": {
            "reference_id": reference_id,
            "source_relative_path": source_relative_path,
            "crop_path": str(crop_path),
            "crop_box_original_px": copy.deepcopy(crop_box),
            "crop_method": viewport["crop_method"],
            "crop_confidence": viewport["confidence"],
            "original_sha256": original_sha256,
            "crop_sha256": crop_sha256,
            "source_claim_ids": copy.deepcopy(candidate.get("source_claim_ids", [])),
            "analysis_record_ids": copy.deepcopy(
                candidate.get("analysis_record_ids", [])
            ),
            "geometry_source": "paddleocr_boxes_and_image_dimensions",
            "owner_approved": False,
            "production_selectable": False,
        },
    }
    blueprint = with_geometry_hash(blueprint)
    validation_errors: list[str] = []
    geometry_contract_valid = False
    if regions and headline_index is None:
        validation_errors.append(
            "headline_candidate_unavailable_without_prompt_brand_or_ui"
        )
    elif regions:
        try:
            validate_layout_blueprint(blueprint)
            geometry_contract_valid = True
        except LayoutBlueprintValidationError as error:
            validation_errors.append(str(error))
    else:
        validation_errors.append("crop_ocr_text_regions_unavailable")
    if not geometry_contract_valid:
        return {
            "schema_version": DRAFT_SCHEMA_VERSION,
            "status": "draft_failed_crop_geometry",
            "reference_id": reference_id,
            "source_relative_path": source_relative_path,
            "viewport_detection": viewport,
            "crop_path": str(crop_path),
            "original_sha256": original_sha256,
            "crop_sha256": crop_sha256,
            "validation_errors": validation_errors,
            "approval_status": "draft_unapproved",
            "owner_approval_receipt_id": None,
            "reference_only": True,
            "production_selectable": False,
            "production_registry_written": False,
            "auto_approval_performed": False,
            "source_files_modified": False,
        }

    receipt_payload = asdict(receipt) if is_dataclass(receipt) else {
        key: _receipt_value(receipt, key, None)
        for key in (
            "success",
            "status",
            "reason",
            "elapsed_seconds",
            "input_unchanged",
            "paddleocr_version",
            "paddlepaddle_version",
            "device",
        )
    }
    return {
        "schema_version": DRAFT_SCHEMA_VERSION,
        "status": "draft_pending_owner_approval",
        "reference_id": reference_id,
        "source_relative_path": source_relative_path,
        "source_image": {
            "width": width,
            "height": height,
            "size_bytes": before.st_size,
            "input_unchanged": source_unchanged,
        },
        "crop_image": {
            "path": str(crop_path),
            "width": crop_width,
            "height": crop_height,
        },
        "viewport_detection": viewport,
        "original_sha256": original_sha256,
        "crop_sha256": crop_sha256,
        "blueprint_draft": blueprint,
        "geometry_contract_valid": geometry_contract_valid,
        "validation_errors": validation_errors,
        "ocr_receipt": {
            "success": bool(_receipt_value(receipt, "success", False)),
            "status": str(_receipt_value(receipt, "status", "")),
            "reason": str(_receipt_value(receipt, "reason", "")),
            "line_count": len(lines),
            "normalized_text_region_count": len(regions),
            "excluded_instagram_ui_region_count": len(excluded_ui_regions),
            "elapsed_seconds": _receipt_value(receipt, "elapsed_seconds", None),
            "runtime": {
                "paddleocr_version": receipt_payload.get("paddleocr_version"),
                "paddlepaddle_version": receipt_payload.get(
                    "paddlepaddle_version"
                ),
                "device": receipt_payload.get("device"),
            },
        },
        "excluded_instagram_ui_regions": excluded_ui_regions,
        "headline_classification": {
            "method": "topness_font_box_short_copy_brand_ui_prompt_density_v2",
            "headline_region_id": (
                f"ocr-text-{headline_index + 1:03d}"
                if headline_index is not None
                else None
            ),
            "scores": headline_scores,
        },
        "media_background_candidates": _media_background_candidates(
            [region["box_norm"] for region in regions]
        ),
        "approval_status": "draft_unapproved",
        "owner_approval_receipt_id": None,
        "reference_only": True,
        "production_selectable": False,
        "production_registry_written": False,
        "auto_approval_performed": False,
        "source_files_modified": False,
    }


def build_reference_geometry_draft_batch(
    candidate_payload: Any,
    *,
    source_root: str | Path,
    output_dir: str | Path,
    ocr_extractor: Callable[..., Any] = extract_korean_text,
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    """Write one draft per candidate plus a non-production index."""

    candidates = extract_reference_draft_candidates(candidate_payload)
    destination = Path(output_dir)
    drafts_dir = destination / "drafts"
    failures_dir = destination / "failures"
    crops_dir = destination / "crops"
    drafts: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for candidate in candidates:
        reference_id = candidate["reference_id"]
        try:
            draft = build_reference_geometry_draft(
                candidate,
                source_root=source_root,
                crop_output_dir=crops_dir,
                ocr_extractor=ocr_extractor,
                timeout_seconds=timeout_seconds,
            )
            if draft["status"] != "draft_pending_owner_approval":
                failure_path = failures_dir / f"{reference_id}.json"
                _atomic_json(failure_path, draft)
                failures.append(
                    {
                        "reference_id": reference_id,
                        "status": draft["status"],
                        "confidence": draft.get(
                            "viewport_detection", {}
                        ).get("confidence"),
                        "failure_path": str(failure_path),
                    }
                )
                continue
            draft_path = drafts_dir / f"{reference_id}.json"
            _atomic_json(draft_path, draft)
            drafts.append(
                {
                    "reference_id": reference_id,
                    "draft_path": str(draft_path),
                    "ocr_status": draft["ocr_receipt"]["status"],
                    "text_region_count": draft["ocr_receipt"][
                        "normalized_text_region_count"
                    ],
                    "geometry_contract_valid": draft[
                        "geometry_contract_valid"
                    ],
                    "confidence": draft["viewport_detection"]["confidence"],
                    "crop_path": draft["crop_image"]["path"],
                    "production_selectable": False,
                }
            )
        except Exception as error:
            failures.append(
                {
                    "reference_id": reference_id,
                    "error": f"{type(error).__name__}: {error}",
                }
            )
    confidence_values = [
        float(item["confidence"])
        for item in drafts + failures
        if isinstance(item.get("confidence"), (int, float))
    ]
    confidence_distribution = {
        "count": len(confidence_values),
        "minimum": round(min(confidence_values), 6)
        if confidence_values
        else None,
        "maximum": round(max(confidence_values), 6)
        if confidence_values
        else None,
        "mean": round(sum(confidence_values) / len(confidence_values), 6)
        if confidence_values
        else None,
        "buckets": {
            "below_0_55": sum(value < 0.55 for value in confidence_values),
            "0_55_to_0_69": sum(
                0.55 <= value < 0.70 for value in confidence_values
            ),
            "0_70_to_0_84": sum(
                0.70 <= value < 0.85 for value in confidence_values
            ),
            "0_85_and_above": sum(
                value >= 0.85 for value in confidence_values
            ),
        },
    }
    index = {
        "schema_version": DRAFT_INDEX_SCHEMA_VERSION,
        "status": "draft_pending_owner_approval",
        "candidate_count": len(candidates),
        "generated_count": len(drafts),
        "failed_count": len(failures),
        "drafts": drafts,
        "failures": failures,
        "confidence_distribution": confidence_distribution,
        "crop_method": CROP_METHOD,
        "full_screenshot_geometry_fallback": False,
        "owner_approval_receipt_id": None,
        "production_selectable": False,
        "production_registry_written": False,
        "auto_approval_performed": False,
        "source_files_modified": False,
    }
    index_path = destination / "reference_geometry_draft_index.json"
    _atomic_json(index_path, index)
    index["index_path"] = str(index_path)
    return index


__all__ = [
    "DRAFT_INDEX_SCHEMA_VERSION",
    "DRAFT_SCHEMA_VERSION",
    "CROP_METHOD",
    "MIN_VIEWPORT_CONFIDENCE",
    "build_reference_geometry_draft",
    "build_reference_geometry_draft_batch",
    "detect_instagram_content_viewport",
]
