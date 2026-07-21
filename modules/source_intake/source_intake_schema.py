"""Source Intake shallow item schema (V1).

Shallow scan contract for the Source Intake & Signal Layer:
- shallow scan is wide and cheap: title / url / rank / visible comparison metrics only
- deep dive (raw_html / screenshots / comments / ad capture) happens ONLY after a
  topic is selected, and is out of scope for V1 (contract constants only)
- metrics must come from parsed page data; missing values stay None, never guessed
- ad signals are text-only (ad_text / ad_domain / ad_category_guess); no ad images
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "source_intake_shallow_v1"

RIGHTS_STATUS_REFERENCE_ONLY = "reference_only"

CHANNEL_CANDIDATES = [
    "issue_daily",
    "love_signal",
    "dopamine_issue",
    "style_weather",
    "commerce_signal",
]

VISIBLE_METRIC_KEYS = [
    "views",
    "comments",
    "likes",
    "dislikes",
    "scraps",
    "shares",
]

DERIVED_METRIC_KEYS = [
    "comment_density",
    "like_rate",
    "controversy_score",
    "velocity_score",
]

MEDIA_FLAG_KEYS = [
    "has_image",
    "image_count",
    "has_video",
]

# Ad signals are limited to text-level hints. Any image/screenshot/file style key
# inside ad_signals is a schema violation by design (cost + rights control).
AD_SIGNAL_ALLOWED_KEYS = ["ad_text", "ad_domain", "ad_category_guess"]
AD_SIGNAL_FORBIDDEN_KEY_PATTERN = re.compile(
    r"(image|img|screenshot|capture|banner_file|path|binary|asset)", re.IGNORECASE
)

# Metric provenance markers. Anything that admits the number was invented is rejected.
METRIC_ORIGIN_ALLOWED = ["parsed", "absent"]
METRIC_ORIGIN_FORBIDDEN = ["fabricated", "estimated", "guessed", "synthetic", "invented"]

SHALLOW_ITEM_REQUIRED_FIELDS = [
    "item_id",
    "source_id",
    "source_type",
    "channel_candidates",
    "board_or_category",
    "title",
    "url",
    "rank_position",
    "published_at",
    "collected_at",
    "visible_metrics",
    "derived_metrics",
    "media_flags",
    "ad_signals",
    "deep_dive_priority",
    "rights_status",
]

# ---------------------------------------------------------------------------
# Storage contract (paths only; V1 writes fixtures/tests, not mass collection)
# ---------------------------------------------------------------------------

SOURCE_INTAKE_STORAGE_ROOT = os.path.join("storage", "source_intake")
SOURCE_DATA_STORAGE_CONFIG_PATH = os.path.join("config", "source_data_storage.json")
DEFAULT_EXTERNAL_SOURCE_DATA_ROOT = "F:/AI-Content-OS-Data"


def source_data_root(config_path: str = SOURCE_DATA_STORAGE_CONFIG_PATH) -> str:
    """Return the external root for large source artifacts.

    Small workflow/index JSON stays inside the repository under storage/.
    Heavy raw material (HTML, screenshots, comment samples, image candidates)
    is routed to this external root so the repo and C: drive stay light.
    """
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            config = json.load(handle)
        root = str(config.get("source_data_root", "")).strip()
        if root:
            return root.replace("\\", "/")
    except Exception:
        pass

    return DEFAULT_EXTERNAL_SOURCE_DATA_ROOT


def deep_dive_external_dir(
    date_str: str,
    stage: str,
    source_id: str = "",
    base_dir: Optional[str] = None,
) -> str:
    """External deep-dive path contract for selected topics only."""
    root = (base_dir or source_data_root()).replace("\\", "/")
    parts = [root, "source_intake", date_str, "deep_dive", stage]
    if source_id:
        parts.append(source_id)
    return os.path.join(*parts)


def shallow_index_dir(date_str: str, base_dir: Optional[str] = None) -> str:
    """storage/source_intake/YYYY-MM-DD/shallow_index/ contract path."""
    root = base_dir if base_dir else SOURCE_INTAKE_STORAGE_ROOT
    return os.path.join(root, date_str, "shallow_index")


# Deep-dive stages have an external writer in V1. Nothing below may be written
# during shallow scan: activation remains owner-selected/approved only.
DEEP_DIVE_STAGE_CONTRACT = {
    "raw_html": {
        "subdir": "deep_dive/raw_html",
        "storage_root": "external_source_data_root",
        "when": "after_topic_selection",
        "enabled_in_v1": True,
        "activation": "owner_selected_only",
    },
    "screenshots": {
        "subdir": "deep_dive/screenshots",
        "storage_root": "external_source_data_root",
        "when": "after_topic_selection",
        "enabled_in_v1": True,
        "activation": "owner_selected_only",
    },
    "comments": {
        "subdir": "deep_dive/comments",
        "storage_root": "external_source_data_root",
        "when": "after_topic_selection",
        "enabled_in_v1": True,
        "activation": "owner_selected_only",
        "note": "V1 stores comment COUNTS only in visible_metrics; comment bodies are deep-dive scope.",
    },
    "ad_capture": {
        "subdir": "deep_dive/ad_signals",
        "storage_root": "external_source_data_root",
        "when": "after_topic_selection",
        "enabled_in_v1": True,
        "activation": "owner_selected_only",
        "note": "Text/domain/category only even in deep dive. Ad images are never captured.",
    },
}


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def empty_visible_metrics() -> Dict[str, Optional[int]]:
    return {key: None for key in VISIBLE_METRIC_KEYS}


def empty_media_flags() -> Dict[str, Any]:
    return {key: None for key in MEDIA_FLAG_KEYS}


def empty_ad_signals() -> Dict[str, Optional[str]]:
    return {key: None for key in AD_SIGNAL_ALLOWED_KEYS}


def empty_derived_metrics() -> Dict[str, Optional[float]]:
    return {key: None for key in DERIVED_METRIC_KEYS}


def _coerce_count(value: Any) -> Optional[int]:
    """Coerce a parsed metric to a non-negative int, or None when unusable.

    Strings like '1,234' from HTML are accepted; anything non-numeric or
    negative becomes None instead of a made-up value.
    """
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value if value >= 0 else None

    if isinstance(value, float):
        if value < 0:
            return None
        return int(value)

    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if cleaned.isdigit():
            return int(cleaned)
        return None

    return None


def build_visible_metrics(raw: Optional[Dict[str, Any]]) -> Dict[str, Optional[int]]:
    metrics = empty_visible_metrics()

    if not isinstance(raw, dict):
        return metrics

    for key in VISIBLE_METRIC_KEYS:
        metrics[key] = _coerce_count(raw.get(key))

    return metrics


def build_media_flags(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    flags = empty_media_flags()

    if not isinstance(raw, dict):
        return flags

    if isinstance(raw.get("has_image"), bool):
        flags["has_image"] = raw["has_image"]

    if isinstance(raw.get("has_video"), bool):
        flags["has_video"] = raw["has_video"]

    flags["image_count"] = _coerce_count(raw.get("image_count"))

    return flags


def build_ad_signals(raw: Optional[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    signals = empty_ad_signals()

    if not isinstance(raw, dict):
        return signals

    for key in AD_SIGNAL_ALLOWED_KEYS:
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            signals[key] = value.strip()

    return signals


def build_shallow_item(
    source_id: str,
    source_type: str,
    title: str,
    url: str,
    rank_position: Optional[int] = None,
    board_or_category: str = "",
    channel_candidates: Optional[List[str]] = None,
    published_at: Optional[str] = None,
    collected_at: Optional[str] = None,
    visible_metrics: Optional[Dict[str, Any]] = None,
    derived_metrics: Optional[Dict[str, Any]] = None,
    media_flags: Optional[Dict[str, Any]] = None,
    ad_signals: Optional[Dict[str, Any]] = None,
    deep_dive_priority: float = 0.0,
) -> Dict[str, Any]:
    """Build a schema-conformant shallow item with safe defaults everywhere."""
    collected = collected_at or datetime.now().isoformat()
    candidates = [
        channel for channel in (channel_candidates or [])
        if channel in CHANNEL_CANDIDATES
    ]

    item = {
        "schema_version": SCHEMA_VERSION,
        "item_id": f"{source_id}:{url}" if url else f"{source_id}:{title}",
        "source_id": source_id,
        "source_type": source_type,
        "channel_candidates": candidates,
        "board_or_category": board_or_category or "",
        "title": title or "",
        "url": url or "",
        "rank_position": _coerce_count(rank_position),
        "published_at": published_at or None,
        "collected_at": collected,
        "visible_metrics": build_visible_metrics(visible_metrics),
        "derived_metrics": dict(empty_derived_metrics(), **(derived_metrics or {})),
        "media_flags": build_media_flags(media_flags),
        "ad_signals": build_ad_signals(ad_signals),
        "deep_dive_priority": float(deep_dive_priority or 0.0),
        "rights_status": RIGHTS_STATUS_REFERENCE_ONLY,
        "metrics_origin": "parsed" if _has_any_metric(visible_metrics) else "absent",
    }

    return item


def _has_any_metric(raw: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(raw, dict):
        return False

    return any(_coerce_count(raw.get(key)) is not None for key in VISIBLE_METRIC_KEYS)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_shallow_item(item: Any) -> Tuple[bool, List[str]]:
    """Validate a shallow item. Returns (is_valid, error_list). Never raises."""
    errors: List[str] = []

    if not isinstance(item, dict):
        return False, ["item_not_a_dict"]

    for field in SHALLOW_ITEM_REQUIRED_FIELDS:
        if field not in item:
            errors.append(f"missing_field:{field}")

    if errors:
        return False, errors

    if not item.get("title"):
        errors.append("empty_title")

    if item.get("rights_status") != RIGHTS_STATUS_REFERENCE_ONLY:
        errors.append("rights_status_must_be_reference_only")

    for channel in item.get("channel_candidates") or []:
        if channel not in CHANNEL_CANDIDATES:
            errors.append(f"unknown_channel:{channel}")

    # --- metric provenance: fabricated markers are rejected outright ---
    origin = item.get("metrics_origin")
    if origin is not None:
        origin_text = str(origin).lower()
        if origin_text in METRIC_ORIGIN_FORBIDDEN:
            errors.append(f"forbidden_metrics_origin:{origin_text}")
        elif origin_text not in METRIC_ORIGIN_ALLOWED:
            errors.append(f"unknown_metrics_origin:{origin_text}")

    if item.get("fabricated_metrics"):
        errors.append("fabricated_metrics_marker_present")

    # --- visible metrics: non-negative int or None only ---
    visible = item.get("visible_metrics")
    if not isinstance(visible, dict):
        errors.append("visible_metrics_not_a_dict")
    else:
        for key in VISIBLE_METRIC_KEYS:
            value = visible.get(key)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int):
                errors.append(f"metric_not_int_or_null:{key}")
            elif value < 0:
                errors.append(f"negative_metric:{key}")

    # --- ad signals: text-only, no image/file style keys ---
    ad_signals = item.get("ad_signals")
    if not isinstance(ad_signals, dict):
        errors.append("ad_signals_not_a_dict")
    else:
        for key in ad_signals:
            if key not in AD_SIGNAL_ALLOWED_KEYS:
                errors.append(f"ad_signal_key_not_allowed:{key}")
            if AD_SIGNAL_FORBIDDEN_KEY_PATTERN.search(str(key)):
                errors.append(f"ad_signal_image_like_key_forbidden:{key}")

    # --- deep dive priority sanity ---
    priority = item.get("deep_dive_priority")
    if not isinstance(priority, (int, float)) or isinstance(priority, bool):
        errors.append("deep_dive_priority_not_numeric")
    elif priority < 0:
        errors.append("deep_dive_priority_negative")

    return (len(errors) == 0), errors


# ---------------------------------------------------------------------------
# Shallow index persistence (fixture/test scale in V1)
# ---------------------------------------------------------------------------

def write_shallow_index(
    items: List[Dict[str, Any]],
    date_str: str,
    source_id: str,
    base_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Write valid items to the shallow_index contract path.

    Invalid items are dropped and reported, never written. Only a single JSON
    file per source is produced — no ad image directories, no raw html.
    """
    target_dir = shallow_index_dir(date_str, base_dir=base_dir)
    valid_items = []
    rejected = []

    for item in items or []:
        ok, item_errors = validate_shallow_item(item)
        if ok:
            valid_items.append(item)
        else:
            rejected.append({"item_id": item.get("item_id") if isinstance(item, dict) else None,
                             "errors": item_errors})

    result = {
        "status": "skipped_empty",
        "path": "",
        "written_count": 0,
        "rejected_count": len(rejected),
        "rejected": rejected,
    }

    if not valid_items:
        return result

    try:
        os.makedirs(target_dir, exist_ok=True)
        path = os.path.join(target_dir, f"{source_id}.json")
        payload = {
            "schema_version": SCHEMA_VERSION,
            "source_id": source_id,
            "date": date_str,
            "generated_at": datetime.now().isoformat(),
            "item_count": len(valid_items),
            "items": valid_items,
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

        result["status"] = "written"
        result["path"] = path
        result["written_count"] = len(valid_items)
    except Exception as error:
        result["status"] = "write_failed"
        result["error"] = str(error)

    return result
