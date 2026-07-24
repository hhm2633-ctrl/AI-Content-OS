"""Single source of truth for Instagram canvas and CardNews count contracts."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Tuple


CardCanvasSize = Tuple[int, int]

DEFAULT_CARD_NEWS_PROFILE_ID = "instagram_portrait_3_4"
DEFAULT_CARD_CANVAS_SIZE: CardCanvasSize = (1080, 1440)

INSTAGRAM_CANVAS_PROFILES: Mapping[str, Mapping[str, Any]] = {
    "instagram_landscape_1_91_1": {
        "profile_id": "instagram_landscape_1_91_1",
        "surface": "feed",
        "width": 1080,
        "height": 566,
        "aspect_ratio": "1.91:1",
        "carousel_compatible": True,
        "safe_previews": {
            "central_square": {"x": 257, "y": 0, "width": 566, "height": 566},
            "profile_grid_3_4": {"x": 328, "y": 0, "width": 424, "height": 566},
        },
    },
    "instagram_square_1_1": {
        "profile_id": "instagram_square_1_1",
        "surface": "feed",
        "width": 1080,
        "height": 1080,
        "aspect_ratio": "1:1",
        "carousel_compatible": True,
        "safe_previews": {
            "central_square": {"x": 0, "y": 0, "width": 1080, "height": 1080},
            "profile_grid_3_4": {"x": 135, "y": 0, "width": 810, "height": 1080},
        },
    },
    "instagram_portrait_3_4": {
        "profile_id": "instagram_portrait_3_4",
        "surface": "feed",
        "width": 1080,
        "height": 1440,
        "aspect_ratio": "3:4",
        "carousel_compatible": True,
        "safe_previews": {
            "central_square": {"x": 0, "y": 180, "width": 1080, "height": 1080},
            "profile_grid_3_4": {"x": 0, "y": 0, "width": 1080, "height": 1440},
        },
    },
    "instagram_fullscreen_9_16": {
        "profile_id": "instagram_fullscreen_9_16",
        "surface": "story_reels",
        "width": 1080,
        "height": 1920,
        "aspect_ratio": "9:16",
        "carousel_compatible": False,
        "safe_previews": {
            "feed_portrait_3_4": {"x": 0, "y": 240, "width": 1080, "height": 1440},
        },
    },
}

CARD_NEWS_PROFILE_IDS = frozenset(
    profile_id
    for profile_id, profile in INSTAGRAM_CANVAS_PROFILES.items()
    if profile["surface"] == "feed" and profile["carousel_compatible"] is True
)
CARD_NEWS_CANVAS_PROFILES: Mapping[str, Mapping[str, Any]] = {
    profile_id: INSTAGRAM_CANVAS_PROFILES[profile_id]
    for profile_id in CARD_NEWS_PROFILE_IDS
}
ALLOWED_CARD_CANVAS_SIZES: frozenset[CardCanvasSize] = frozenset(
    (int(profile["width"]), int(profile["height"]))
    for profile in CARD_NEWS_CANVAS_PROFILES.values()
)

MIN_ALLOWED_CARD_SLIDE_COUNT = 1
MAX_ALLOWED_CARD_SLIDE_COUNT = 20
ALLOWED_CARD_SLIDE_COUNT_RANGE = (MIN_ALLOWED_CARD_SLIDE_COUNT, MAX_ALLOWED_CARD_SLIDE_COUNT)


def is_allowed_card_canvas_size(size: Iterable[int]) -> bool:
    """Return True when ``size`` is one of the approved CardNews canvases."""
    try:
        width, height = size
    except (TypeError, ValueError):
        return False
    return (width, height) in ALLOWED_CARD_CANVAS_SIZES


def get_card_canvas_profile(
    profile_id: str = DEFAULT_CARD_NEWS_PROFILE_ID,
) -> Mapping[str, Any] | None:
    """Return one approved feed/carousel profile from the central contract."""
    return CARD_NEWS_CANVAS_PROFILES.get(profile_id)


def card_canvas_size(
    profile_id: str = DEFAULT_CARD_NEWS_PROFILE_ID,
) -> CardCanvasSize | None:
    profile = get_card_canvas_profile(profile_id)
    if profile is None:
        return None
    return int(profile["width"]), int(profile["height"])


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
