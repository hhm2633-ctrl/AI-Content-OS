"""Shared CardNews canvas-size and card-count contracts."""

from __future__ import annotations

from typing import Iterable, Tuple


CardCanvasSize = Tuple[int, int]

ALLOWED_CARD_CANVAS_SIZES: frozenset[CardCanvasSize] = frozenset(
    {
        (1080, 1080),
        (1080, 1350),
        (1080, 1440),
    }
)

MIN_ALLOWED_CARD_SLIDE_COUNT = 2
MAX_ALLOWED_CARD_SLIDE_COUNT = 20
ALLOWED_CARD_SLIDE_COUNT_RANGE = (MIN_ALLOWED_CARD_SLIDE_COUNT, MAX_ALLOWED_CARD_SLIDE_COUNT)


def is_allowed_card_canvas_size(size: Iterable[int]) -> bool:
    """Return True when ``size`` is one of the approved CardNews canvases."""
    try:
        width, height = size
    except (TypeError, ValueError):
        return False
    return (width, height) in ALLOWED_CARD_CANVAS_SIZES


def allowed_card_canvas_sizes_label() -> str:
    return ", ".join(
        f"{width}x{height}" for width, height in sorted(ALLOWED_CARD_CANVAS_SIZES)
    )


def is_allowed_card_slide_count(count: int) -> bool:
    """Return True when ``count`` is within the approved slide-count bounds."""
    return (
        isinstance(count, int)
        and MIN_ALLOWED_CARD_SLIDE_COUNT <= count <= MAX_ALLOWED_CARD_SLIDE_COUNT
    )


def allowed_card_slide_count_label() -> str:
    return f"{MIN_ALLOWED_CARD_SLIDE_COUNT}..{MAX_ALLOWED_CARD_SLIDE_COUNT}"
