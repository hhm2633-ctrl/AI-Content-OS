"""Extract subject bounding boxes from rembg alpha channels.

This module intentionally stays dependency-light and focused: only bounding-box
extraction from an RGBA image (typically a rembg output) with a simple largest
connected-component strategy.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Literal

from PIL import Image


ALPHA_COMPONENT_SELECTION = Literal["largest", "all"]
DEFAULT_ALPHA_THRESHOLD = 8
DEFAULT_MIN_AREA = 400
DEFAULT_MARGIN_RATIO = 0.0


@dataclass(frozen=True)
class _Component:
    area: int
    x1: int
    y1: int
    x2: int
    y2: int


def _expand_bbox(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    width: int,
    height: int,
    margin_ratio: float,
) -> tuple[int, int, int, int]:
    if margin_ratio <= 0:
        return x1, y1, x2, y2
    span = max(width, height)
    margin = int(max(1, round(span * margin_ratio)))
    return (
        max(0, x1 - margin),
        max(0, y1 - margin),
        min(width, x2 + margin),
        min(height, y2 + margin),
    )


def _find_components(
    alpha_bytes: bytes,
    width: int,
    height: int,
    *,
    alpha_threshold: int,
) -> list[_Component]:
    visited = bytearray(len(alpha_bytes))
    components: list[_Component] = []

    for index in range(len(alpha_bytes)):
        if visited[index] or alpha_bytes[index] <= alpha_threshold:
            continue

        queue: deque[int] = deque([index])
        visited[index] = 1

        area = 0
        x1 = width
        y1 = height
        x2 = 0
        y2 = 0

        while queue:
            current = queue.popleft()
            y = current // width
            x = current % width
            area += 1

            if x < x1:
                x1 = x
            if x > x2:
                x2 = x
            if y < y1:
                y1 = y
            if y > y2:
                y2 = y

            neighbors = (current - 1, current + 1, current - width, current + width)
            for next_index in neighbors:
                if next_index < 0 or next_index >= len(alpha_bytes):
                    continue
                if visited[next_index] or alpha_bytes[next_index] <= alpha_threshold:
                    continue

                nx = next_index % width
                ny = next_index // width
                if abs(nx - x) + abs(ny - y) != 1:
                    continue

                visited[next_index] = 1
                queue.append(next_index)

        components.append(_Component(area=area, x1=x1, y1=y1, x2=x2 + 1, y2=y2 + 1))

    return components


def extract_subject_bbox_from_alpha(
    image_path: str | Path,
    *,
    alpha_threshold: int = DEFAULT_ALPHA_THRESHOLD,
    min_area: int = DEFAULT_MIN_AREA,
    component: ALPHA_COMPONENT_SELECTION = "largest",
    margin_ratio: float = DEFAULT_MARGIN_RATIO,
    include_normalized: bool = True,
) -> Dict[str, Any]:
    """Extract subject bbox from rembg alpha channel.

    Args:
        image_path: PNG/JPEG path; expected to contain RGBA alpha (or converted).
        alpha_threshold: Non-zero alpha is considered foreground if > threshold.
        min_area: Ignore components smaller than this pixel count.
        component: currently only ``largest`` is supported.
        margin_ratio: ratio to expand selected bbox by (ratio of max(width,height)).
        include_normalized: include [0,1] normalized bbox keys.
    """

    if alpha_threshold < 0 or alpha_threshold > 255:
        return {"status": "failed", "reason": "invalid_alpha_threshold", "alpha_threshold": alpha_threshold}
    if component not in {"largest", "all"}:
        return {"status": "failed", "reason": "unsupported_component_selector", "component": component}
    if min_area < 1:
        return {"status": "failed", "reason": "invalid_min_area", "min_area": min_area}
    if margin_ratio < 0:
        return {"status": "failed", "reason": "invalid_margin_ratio", "margin_ratio": margin_ratio}

    path = Path(image_path)
    try:
        with Image.open(path) as image:
            rgba = image.convert("RGBA")
    except OSError as error:
        return {"status": "failed", "reason": "image_open_failed", "detail": str(error)[:400]}

    width, height = rgba.size
    alpha = rgba.getchannel("A")
    alpha_bytes = alpha.tobytes()

    components = _find_components(alpha_bytes, width, height, alpha_threshold=alpha_threshold)
    if not components:
        return {"status": "failed", "reason": "no_alpha_foreground"}

    candidates = [component for component in components if component.area >= min_area]
    if not candidates:
        return {
            "status": "failed",
            "reason": "no_component_above_min_area",
            "component_count": len(components),
            "max_area": max((component.area for component in components), default=0),
            "min_area": min_area,
        }

    if component == "all":
        selected = sorted(candidates, key=lambda item: item.area, reverse=True)
    else:
        selected = [max(candidates, key=lambda item: item.area)]

    bboxes = []
    for index, item in enumerate(selected, start=1):
        x1, y1, x2, y2 = _expand_bbox(
            item.x1,
            item.y1,
            item.x2,
            item.y2,
            width,
            height,
            margin_ratio,
        )
        bbox: Dict[str, int] = {
            "x": int(x1),
            "y": int(y1),
            "width": int(x2 - x1),
            "height": int(y2 - y1),
        }
        entry: Dict[str, Any] = {
            "index": index,
            "area": int(item.area),
            "bbox": bbox,
            "bbox_xyxy": {
                "x1": int(x1),
                "y1": int(y1),
                "x2": int(x2),
                "y2": int(y2),
            },
        }
        if include_normalized:
            entry["bbox_normalized"] = {
                "x": x1 / width if width else 0.0,
                "y": y1 / height if height else 0.0,
                "width": (x2 - x1) / width if width else 0.0,
                "height": (y2 - y1) / height if height else 0.0,
            }
        bboxes.append(entry)

    return {
        "status": "ok",
        "source": str(path),
        "image_size": {"width": width, "height": height},
        "alpha_threshold": int(alpha_threshold),
        "min_area": int(min_area),
        "margin_ratio": float(margin_ratio),
        "component_selector": component,
        "component_count": len(components),
        "accepted_components": len(candidates),
        "selected_count": len(selected),
        "selected": bboxes,
        "primary_bbox": bboxes[0]["bbox"],
        "primary_bbox_xyxy": bboxes[0]["bbox_xyxy"],
    }


__all__ = [
    "extract_subject_bbox_from_alpha",
    "_find_components",
    "_expand_bbox",
]
