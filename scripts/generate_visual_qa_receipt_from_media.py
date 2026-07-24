"""Generate representative visual QA receipt payloads from rendered slide media.

This helper is intentionally isolated from controller/qa gate internals. It reads a
production-style manifest, runs OpenCLIP + PaddleOCR against each expected slide,
and emits a qa_receipt.json shaped for the existing `accept-visual-qa` flow.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
import os
import re
import tempfile
import time
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from types import SimpleNamespace
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

from modules.card_news.visual_qa_gate import REQUIRED_FINDINGS, assess_visual_qa_receipt
from modules.media_intelligence.rembg_bbox import extract_subject_bbox_from_alpha
from modules.tool_adapters.rembg_runtime import RembgRuntimeAdapter
from modules.tool_adapters.openclip_runtime import OpenClipRuntime
from modules.tool_adapters.paddleocr_runtime import extract_korean_text
from scripts.run_cardnews_production import (
    SUBJECT_CROP_GUARD_MAX_SUBJECT_OUTSIDE_RATIO,
    SUBJECT_CROP_GUARD_METRIC_PRECISION,
    _evaluate_subject_crop_guard,
    _expected_slides,
)

PASS = "pass"
NOT_APPLICABLE = "not_applicable"
FAIL = "fail"
IMAGE_IS_PRIMARY_AREA_THRESHOLD = 0.15
EXPECTED_COPY_COVERAGE_MIN = 0.55
SAFE_AREA_SIDE_RATIO = 0.02
SAFE_AREA_TOP_RATIO = 0.02
SAFE_AREA_BOTTOM_RATIO = 0.035
DETAIL_BLANKNESS_THRESHOLD = 0.32
DETAIL_TEXT_AREA_MIN = 0.08
DETAIL_TEXT_CHAR_MIN = 72
DETAIL_TEXT_LINE_MIN = 4
VISUAL_QA_MODEL_CACHE_SCHEMA = "cardnews_visual_qa_model_cache_v1"
VISUAL_QA_MODEL_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
DEFAULT_VISUAL_QA_CACHE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "storage"
    / "cache"
    / "cardnews_visual_qa"
)
MAX_VISUAL_QA_WORKERS = 4


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_hash(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _visual_qa_model_config(
    openclip_probe: Mapping[str, Any],
    *,
    openclip_timeout: float,
    ocr_timeout: float,
) -> Dict[str, Any]:
    openclip_model = (
        openclip_probe.get("model")
        if isinstance(openclip_probe.get("model"), Mapping)
        else {}
    )
    config = {
        "cache_schema": VISUAL_QA_MODEL_CACHE_SCHEMA,
        "engines": {
            "paddleocr": {
                "engine": "paddleocr",
                "model": os.getenv(
                    "AI_CONTENT_OS_PADDLEOCR_MODEL",
                    "korean-default",
                ),
                "version": os.getenv(
                    "AI_CONTENT_OS_PADDLEOCR_VERSION",
                    "paddleocr_runtime_v1",
                ),
            },
            "openclip": {
                "engine": "openclip",
                "model": _text(openclip_model.get("model_name"))
                or "RN50-quickgelu",
                "version": _text(openclip_model.get("revision"))
                or "unknown-revision",
                "weights_sha256": _text(openclip_model.get("sha256")),
            },
        },
        "timeouts": {
            "openclip_seconds": float(openclip_timeout),
            "ocr_seconds": float(ocr_timeout),
        },
        "qa_rules": {
            "image_primary_area_threshold": IMAGE_IS_PRIMARY_AREA_THRESHOLD,
            "expected_copy_coverage_min": EXPECTED_COPY_COVERAGE_MIN,
            "safe_area_side_ratio": SAFE_AREA_SIDE_RATIO,
            "safe_area_top_ratio": SAFE_AREA_TOP_RATIO,
            "safe_area_bottom_ratio": SAFE_AREA_BOTTOM_RATIO,
            "detail_blankness_threshold": DETAIL_BLANKNESS_THRESHOLD,
            "detail_text_area_min": DETAIL_TEXT_AREA_MIN,
            "detail_text_char_min": DETAIL_TEXT_CHAR_MIN,
            "detail_text_line_min": DETAIL_TEXT_LINE_MIN,
        },
    }
    config["config_hash"] = _stable_hash(config)
    return config


def _visual_qa_cache_key(
    *,
    image_sha256: str,
    expected_copy: str,
    semantic_context: Mapping[str, Any],
    config_hash: str,
) -> str:
    return _stable_hash(
        {
            "image_sha256": image_sha256,
            "expected_copy": unicodedata.normalize("NFKC", expected_copy),
            "semantic_context": dict(semantic_context),
            "config_hash": config_hash,
        }
    )


def _model_evidence_cacheable(evidence: Mapping[str, Any]) -> bool:
    ocr = evidence.get("ocr")
    openclip = evidence.get("openclip_result")
    return bool(
        isinstance(ocr, Mapping)
        and ocr.get("success") is True
        and _text(ocr.get("status")) == "completed"
        and isinstance(openclip, Mapping)
        and _text(openclip.get("status")) == "completed"
    )


def _load_visual_qa_model_cache(
    cache_path: Path,
    *,
    cache_key: str,
    config_hash: str,
    now: float | None = None,
) -> Dict[str, Any] | None:
    if not cache_path.is_file():
        return None
    current_time = time.time() if now is None else now
    try:
        if current_time - cache_path.stat().st_mtime > VISUAL_QA_MODEL_CACHE_TTL_SECONDS:
            return None
        payload = _read_json(cache_path)
    except (OSError, json.JSONDecodeError):
        return None
    if (
        not isinstance(payload, Mapping)
        or payload.get("schema_version") != VISUAL_QA_MODEL_CACHE_SCHEMA
        or _text(payload.get("cache_key")) != cache_key
        or _text(payload.get("config_hash")) != config_hash
    ):
        return None
    evidence = payload.get("model_evidence")
    if not isinstance(evidence, Mapping) or not _model_evidence_cacheable(evidence):
        return None
    return deepcopy(dict(evidence))


def _write_visual_qa_model_cache(
    cache_path: Path,
    *,
    cache_key: str,
    config: Mapping[str, Any],
    image_sha256: str,
    expected_copy: str,
    model_evidence: Mapping[str, Any],
) -> bool:
    if not _model_evidence_cacheable(model_evidence):
        return False
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": VISUAL_QA_MODEL_CACHE_SCHEMA,
        "cache_key": cache_key,
        "config_hash": _text(config.get("config_hash")),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "ttl_seconds": VISUAL_QA_MODEL_CACHE_TTL_SECONDS,
        "image_sha256": image_sha256,
        "expected_copy_sha256": hashlib.sha256(
            expected_copy.encode("utf-8")
        ).hexdigest(),
        "engine_config": deepcopy(dict(config)),
        "model_evidence": deepcopy(dict(model_evidence)),
    }
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".tmp",
            prefix=f"{cache_path.stem}.",
            dir=cache_path.parent,
            delete=False,
        ) as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            temporary_path = Path(handle.name)
        temporary_path.replace(cache_path)
        return True
    except OSError:
        return False
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink(missing_ok=True)


def _bounded_ordered_map(
    rows: Sequence[Any],
    worker: Any,
    *,
    max_workers: int,
) -> list[Any]:
    bounded_workers = max(
        1,
        min(int(max_workers), MAX_VISUAL_QA_WORKERS, len(rows) or 1),
    )
    if bounded_workers == 1:
        return [worker(row) for row in rows]
    with ThreadPoolExecutor(max_workers=bounded_workers) as executor:
        return list(executor.map(worker, rows))


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _coerce_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _box_area(box: Sequence[float]) -> float:
    if len(box) < 4:
        return 0.0
    x1, y1, x2, y2 = box[:4]
    width = max(0.0, x2 - x1)
    height = max(0.0, y2 - y1)
    return width * height


def _polygon_area(points: Sequence[Sequence[float]]) -> float:
    if len(points) < 3:
        return 0.0
    area = 0.0
    for index, point in enumerate(points):
        point_x = point[0] if len(point) > 0 else 0.0
        point_y = point[1] if len(point) > 1 else 0.0
        next_point = points[(index + 1) % len(points)]
        next_x = next_point[0] if len(next_point) > 0 else 0.0
        next_y = next_point[1] if len(next_point) > 1 else 0.0
        area += point_x * next_y - next_x * point_y
    return abs(area) * 0.5


def _text_area_ratio(
    boxes: Sequence[Sequence[float]],
    polys: Sequence[Sequence[Sequence[float]]],
    width: float,
    height: float,
) -> float:
    if width <= 0 or height <= 0:
        return 0.0
    image_area = width * height
    total_area = 0.0
    if boxes:
        for item in boxes:
            area = _box_area([_coerce_float(value) for value in item])
            if area > 0:
                total_area += area
    elif polys:
        for polygon in polys:
            area = _polygon_area(
                [[_coerce_float(point[0]), _coerce_float(point[1])] for point in polygon]
            )
            if area > 0:
                total_area += area
    ratio = total_area / image_area
    return min(1.0, ratio)


def _normalize_copy(value: Any) -> str:
    normalized = unicodedata.normalize("NFKC", _text(value)).casefold()
    return "".join(re.findall(r"[0-9a-z가-힣]+", normalized))


def _copy_tokens(value: Any) -> list[str]:
    normalized = unicodedata.normalize("NFKC", _text(value)).casefold()
    return [
        token
        for token in re.findall(r"[0-9a-z가-힣]+", normalized)
        if len(token) >= 2
    ]


def _copy_integrity(
    package_slide: Mapping[str, Any] | None,
    ocr_text: str,
    ocr_lines: Sequence[str],
    *,
    ocr_success: bool,
    ocr_status: str,
) -> Dict[str, Any]:
    headline = _text(package_slide.get("headline")) if package_slide else ""
    body = _text(package_slide.get("body")) if package_slide else ""
    expected_tokens = list(dict.fromkeys(_copy_tokens(f"{headline} {body}")))
    ocr_normalized = _normalize_copy(ocr_text)
    matched_tokens = [
        token for token in expected_tokens if _normalize_copy(token) in ocr_normalized
    ]
    expected_weight = sum(len(token) for token in expected_tokens)
    matched_weight = sum(len(token) for token in matched_tokens)
    coverage = matched_weight / expected_weight if expected_weight else 1.0
    coverage_enforced = bool(
        ocr_success
        and ocr_status == "completed"
        and expected_weight >= 12
    )

    headline_normalized = _normalize_copy(headline)
    body_normalized = _normalize_copy(body)
    expected_duplicate = bool(
        len(headline_normalized) >= 10
        and body_normalized.startswith(headline_normalized)
    )
    normalized_lines = [
        normalized
        for line in ocr_lines
        if len(normalized := _normalize_copy(line)) >= 8
    ]
    repeated_lines = sorted(
        line for line, count in Counter(normalized_lines).items() if count > 1
    )
    duplicate_detected = bool(expected_duplicate or repeated_lines)
    missing_copy = bool(
        coverage_enforced and coverage < EXPECTED_COPY_COVERAGE_MIN
    )
    reason_codes = []
    if missing_copy:
        reason_codes.append("expected_copy_coverage_below_minimum")
    if expected_duplicate:
        reason_codes.append("headline_repeated_at_body_start")
    if repeated_lines:
        reason_codes.append("ocr_line_repeated")

    return {
        "passed": not missing_copy and not duplicate_detected,
        "coverage_enforced": coverage_enforced,
        "expected_copy_coverage": round(coverage, 4),
        "minimum_expected_copy_coverage": EXPECTED_COPY_COVERAGE_MIN,
        "expected_token_count": len(expected_tokens),
        "matched_token_count": len(matched_tokens),
        "missing_tokens": [
            token for token in expected_tokens if token not in matched_tokens
        ][:20],
        "duplicate_detected": duplicate_detected,
        "expected_duplicate": expected_duplicate,
        "repeated_ocr_lines": repeated_lines[:10],
        "reason_codes": reason_codes,
    }


def _ocr_line_matches_expected_copy(line: str, expected_copy: str) -> bool:
    line_normalized = _normalize_copy(line)
    expected_normalized = _normalize_copy(expected_copy)
    if len(line_normalized) < 2 or not expected_normalized:
        return False
    if line_normalized in expected_normalized:
        return True

    line_tokens = set(_copy_tokens(line))
    expected_tokens = set(_copy_tokens(expected_copy))
    matched_weight = sum(
        len(token) for token in line_tokens if token in expected_tokens
    )
    return matched_weight >= 3 and matched_weight / len(line_normalized) >= 0.5


def _ocr_geometry_safety(
    boxes: Sequence[Sequence[float]],
    polys: Sequence[Sequence[Sequence[float]]],
    width: float,
    height: float,
    *,
    ocr_lines: Sequence[str] = (),
    expected_copy: str = "",
    expected_copy_only: bool = False,
) -> Dict[str, Any]:
    bounds: list[tuple[int, float, float, float, float]] = []
    for index, box in enumerate(boxes or ()):
        if len(box) >= 4:
            values = [_coerce_float(value) for value in box[:4]]
            bounds.append((index, values[0], values[1], values[2], values[3]))
    if not bounds:
        for index, polygon in enumerate(polys or ()):
            points = [
                (_coerce_float(point[0]), _coerce_float(point[1]))
                for point in polygon
                if len(point) >= 2
            ]
            if points:
                xs = [point[0] for point in points]
                ys = [point[1] for point in points]
                bounds.append((index, min(xs), min(ys), max(xs), max(ys)))

    total_box_count = len(bounds)
    matched_line_indexes: set[int] = set()
    if expected_copy_only:
        matched_line_indexes = {
            index
            for index, line in enumerate(ocr_lines)
            if _ocr_line_matches_expected_copy(_text(line), expected_copy)
        }
        bounds = [
            bound for bound in bounds if bound[0] in matched_line_indexes
        ]

    if width <= 0 or height <= 0 or not bounds:
        return {
            "passed": True,
            "evaluated": False,
            "reason_codes": [],
            "box_count": len(bounds),
            "total_box_count": total_box_count,
            "ignored_source_text_box_count": (
                total_box_count - len(bounds) if expected_copy_only else 0
            ),
            "scope": (
                "expected_overlay_copy_only"
                if expected_copy_only
                else "all_ocr_text"
            ),
        }

    safe_left = width * SAFE_AREA_SIDE_RATIO
    safe_right = width * (1.0 - SAFE_AREA_SIDE_RATIO)
    safe_top = height * SAFE_AREA_TOP_RATIO
    safe_bottom = height * (1.0 - SAFE_AREA_BOTTOM_RATIO)
    violations = []
    for source_index, x1, y1, x2, y2 in bounds:
        edges = []
        if x1 < safe_left:
            edges.append("left")
        if x2 > safe_right:
            edges.append("right")
        if y1 < safe_top:
            edges.append("top")
        if y2 > safe_bottom:
            edges.append("bottom")
        if edges:
            violations.append(
                {
                    "index": source_index,
                    "edges": edges,
                    "bbox": [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
                }
            )

    return {
        "passed": not violations,
        "evaluated": True,
        "box_count": len(bounds),
        "total_box_count": total_box_count,
        "ignored_source_text_box_count": (
            total_box_count - len(bounds) if expected_copy_only else 0
        ),
        "scope": (
            "expected_overlay_copy_only"
            if expected_copy_only
            else "all_ocr_text"
        ),
        "matched_line_indexes": (
            sorted(matched_line_indexes) if expected_copy_only else []
        ),
        "safe_area": {
            "left": round(safe_left, 2),
            "right": round(safe_right, 2),
            "top": round(safe_top, 2),
            "bottom": round(safe_bottom, 2),
        },
        "violations": violations,
        "reason_codes": ["ocr_bbox_outside_safe_area"] if violations else [],
    }


def _package_slide_has_media(
    package_slide: Mapping[str, Any] | None,
    rendered_slide: Mapping[str, Any],
) -> bool:
    if any(
        rendered_slide.get(field)
        for field in ("rendered_asset_id", "rendered_asset_path", "asset_path")
    ):
        return True
    if not package_slide:
        return False
    asset_refs = package_slide.get("asset_refs")
    if isinstance(asset_refs, Sequence) and not isinstance(asset_refs, (str, bytes)):
        if any(_text(value) for value in asset_refs):
            return True
    visual_spec = package_slide.get("visual_spec")
    if isinstance(visual_spec, Mapping):
        return any(
            visual_spec.get(field)
            for field in ("asset_id", "asset_path", "source_asset_id", "source_media")
        )
    return False


def _is_source_media_lower_third(
    package_slide: Mapping[str, Any] | None,
) -> bool:
    if not package_slide:
        return False
    visual_spec = package_slide.get("visual_spec")
    if not isinstance(visual_spec, Mapping):
        return False
    visual_type = _text(visual_spec.get("visual_type")).lower()
    source_media = visual_spec.get("source_media_candidate")
    return bool(
        isinstance(source_media, Mapping)
        and (
            visual_type == "cover_editorial"
            or "lower_third" in visual_type
        )
    )


def _lower_third_expected_overlay_indexes(
    ocr_lines: Sequence[str],
    boxes: Sequence[Sequence[float]],
    polys: Sequence[Sequence[Sequence[float]]],
    expected_copy: str,
    height: float,
) -> list[int]:
    if height <= 0:
        return []
    minimum_overlay_y = height * 0.35
    selected: list[int] = []
    for index, line in enumerate(ocr_lines):
        if not _ocr_line_matches_expected_copy(_text(line), expected_copy):
            continue
        y1 = 0.0
        y2 = 0.0
        if index < len(boxes) and len(boxes[index]) >= 4:
            y1 = _coerce_float(boxes[index][1])
            y2 = _coerce_float(boxes[index][3])
        elif index < len(polys):
            ys = [
                _coerce_float(point[1])
                for point in polys[index]
                if len(point) >= 2
            ]
            if ys:
                y1, y2 = min(ys), max(ys)
        if y2 > y1 and ((y1 + y2) * 0.5) >= minimum_overlay_y:
            selected.append(index)
    return selected


def _candidate_feed_caption(
    candidate_id: str,
    package: Mapping[str, Any] | None,
    feed_caption_by_candidate: Mapping[str, Any] | None,
) -> str:
    if isinstance(feed_caption_by_candidate, Mapping):
        mapped_caption = _text(feed_caption_by_candidate.get(candidate_id))
        if mapped_caption:
            return mapped_caption
    return _text(package.get("feed_caption")) if isinstance(package, Mapping) else ""


def _feed_caption_finding(
    candidate_id: str,
    resolved_feed_caption_by_candidate: Mapping[str, Any],
) -> str:
    return (
        PASS
        if _text(resolved_feed_caption_by_candidate.get(candidate_id))
        else FAIL
    )


def _receipt_scope(
    candidates: Sequence[str],
    accounts: Sequence[str],
    representative_receipt_ids: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    if len(candidates) == 1 and len(accounts) == 1:
        return {
            "kind": "representative",
            "accounts": list(accounts),
            "candidate_ids": list(candidates),
        }
    normalized_receipt_ids = {
        _text(account): _text(receipt_id)
        for account, receipt_id in (
            representative_receipt_ids.items()
            if isinstance(representative_receipt_ids, Mapping)
            else ()
        )
        if _text(account) and _text(receipt_id)
    }
    return {
        "kind": "batch",
        "accounts": list(accounts),
        "candidate_ids": list(candidates),
        "representative_receipt_ids": normalized_receipt_ids,
    }


def _assess_final_receipt(
    receipt: Mapping[str, Any],
    expected: Sequence[Mapping[str, Any]],
    *,
    output_set_id: str,
    scope: Mapping[str, Any],
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    final_receipt = deepcopy(dict(receipt))
    assessed = assess_visual_qa_receipt(
        final_receipt,
        expected,
        expected_output_set_id=output_set_id,
        expected_representative_receipt_ids=(
            scope.get("representative_receipt_ids")
            if scope.get("kind") == "batch"
            else None
        ),
        require_owner_approval=False,
    )
    return final_receipt, assessed


def _iter_candidates(
    manifest: Mapping[str, Any],
    candidate_filter: set[str] | None,
) -> Iterable[Mapping[str, Any]]:
    for record in manifest.get("records", []):
        if not isinstance(record, Mapping):
            continue
        candidate_id = _text(record.get("candidate_id"))
        if not candidate_id:
            continue
        if candidate_filter and candidate_id not in candidate_filter:
            continue
        yield record


def _load_packages(
    manifest: Mapping[str, Any],
    candidates: set[str] | None,
) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for record in manifest.get("records", []):
        if not isinstance(record, Mapping):
            continue
        candidate_id = _text(record.get("candidate_id"))
        if not candidate_id:
            continue
        if candidates and candidate_id not in candidates:
            continue
        package_path = Path(_text(record.get("package_path")))
        if not package_path.is_file():
            continue
        try:
            package = _read_json(package_path)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(package, Mapping):
            out[candidate_id] = package
    return out


def _candidate_title(package: Mapping[str, Any]) -> str:
    if not isinstance(package, Mapping):
        return ""
    candidate = package.get("candidate")
    if isinstance(candidate, Mapping):
        return _text(candidate.get("title") or candidate.get("summary"))
    story = package.get("story")
    if isinstance(story, Mapping):
        return _text(story.get("summary") or story.get("title"))
    return _text(package.get("title") or package.get("story"))


def _candidate_category(package: Mapping[str, Any]) -> str:
    if not isinstance(package, Mapping):
        return ""
    candidate = package.get("candidate")
    if isinstance(candidate, Mapping):
        return _text(candidate.get("category"))
    return _text(package.get("category"))


def _collect_topics(
    package: Mapping[str, Any],
    slide: Mapping[str, Any],
    candidate_title: str,
    account: str,
    category: str,
) -> list[str]:
    role = _text(slide.get("role"))
    headline = _text(slide.get("headline"))
    body = _text(slide.get("body"))
    topics: list[str] = []

    for value in (
        candidate_title,
        category,
        account,
        role,
        headline,
        body,
    ):
        if value:
            topics.append(value)

    media_payload = slide.get("media") if isinstance(slide, Mapping) else None
    if isinstance(media_payload, str):
        topics.append(media_payload)
    elif isinstance(media_payload, Mapping):
        media_text = " ".join(
            _text(media_payload.get(k))
            for k in ("type", "asset_id", "direction", "credit")
            if _text(media_payload.get(k))
        )
        if media_text:
            topics.append(media_text)

    # Keep OpenCLIP input bounded and stable.
    return [item[:180] for item in topics[:6] if item]


def _sample_signal(path: Path) -> Tuple[bool, Dict[str, Any]]:
    """Simple local signal from image statistics and size."""
    from PIL import Image, ImageStat

    try:
        image = Image.open(path).convert("RGB")
        stat = ImageStat.Stat(image)
        width, height = image.size
        mean_gray = float(mean([v / 255.0 for v in stat.mean]))
        std_gray = float(mean([v / 255.0 for v in stat.stddev]))
        density = max(0.0, min(1.0, 1.0 - mean_gray * 0.5 + std_gray))
        return density >= 0.20, {
            "width": int(width),
            "height": int(height),
            "mean_gray": round(mean_gray, 6),
            "std_gray": round(std_gray, 6),
            "blankness_proxy": round(1.0 - density, 6),
        }
    except Exception as exc:
        return False, {
            "error": f"{type(exc).__name__}:{exc}",
        }


def _read_subject_bbox_from_image(path: Path) -> Dict[str, Any]:
    temp_fd, temp_path = tempfile.mkstemp(prefix="subject-bbox-", suffix=".png")
    os.close(temp_fd)
    cutout_path = Path(temp_path)
    try:
        if cutout_path.exists():
            cutout_path.unlink()
        adapter = RembgRuntimeAdapter()
        readiness = adapter.readiness()
        if readiness.get("status") != "ready":
            return {
                "status": "rembg_not_ready",
                "detail": readiness,
            }
        result = adapter.cutout(path, cutout_path)
        if result.get("status") != "completed":
            return {
                "status": "rembg_failed",
                "detail": result,
            }
        return extract_subject_bbox_from_alpha(
            cutout_path,
            alpha_threshold=8,
            min_area=200,
            component="largest",
            margin_ratio=0.01,
        )
    except Exception as exc:  # pragma: no cover - defensive for tool/runtime variance
        return {
            "status": "rembg_exception",
            "reason": f"{type(exc).__name__}:{exc}",
        }
    finally:
        if cutout_path.exists():
            cutout_path.unlink()


def _analyze_slide(
    slide: Mapping[str, Any],
    package: Mapping[str, Any] | None,
    *,
    openclip_runtime: OpenClipRuntime,
    openclip_timeout: float,
    ocr_timeout: float,
    default_account: str = "",
    default_candidate_title: str = "",
    cached_model_evidence: Mapping[str, Any] | None = None,
    model_evidence_capture: Dict[str, Any] | None = None,
) -> Tuple[Dict[str, str], Dict[str, Any], Dict[str, float]]:
    image_path = Path(_text(slide.get("image_path")))
    findings: Dict[str, str] = {}
    analysis: Dict[str, Any] = {}
    metrics: Dict[str, float] = {}

    if not image_path.is_file():
        findings.update(
                {
                    missing: FAIL for missing in (
                        "mobile_readability",
                        "copy_density_ok",
                        "copy_readability",
                        "image_is_primary",
                        "content_not_blank",
                        "subject_focus",
                        "subject_crop_preserved",
                        "story_progression",
                    )
            }
        )
        return findings, {"image_error": "missing_image_file", "analysis_contract": "missing_media"}, metrics

    non_blank, signal = _sample_signal(image_path)
    analysis["visual_signal"] = signal

    cached_ocr = (
        cached_model_evidence.get("ocr")
        if isinstance(cached_model_evidence, Mapping)
        and isinstance(cached_model_evidence.get("ocr"), Mapping)
        else None
    )
    if cached_ocr is not None:
        ocr = SimpleNamespace(**deepcopy(dict(cached_ocr)))
    else:
        ocr = extract_korean_text(
            image_path,
            timeout_seconds=ocr_timeout,
        )
    ocr_status = _text(ocr.status)
    ocr_lines = list(getattr(ocr, "lines", ()))
    ocr_boxes = getattr(ocr, "boxes", ())
    ocr_polys = getattr(ocr, "polys", ())
    ocr_scores = [
        float(value)
        for value in getattr(ocr, "scores", ())
        if isinstance(value, (float, int))
    ]
    ocr_text = _text(ocr.text)
    ocr_avg = sum(ocr_scores) / len(ocr_scores) if ocr_scores else 0.0

    text_area_ratio = _text_area_ratio(
        ocr_boxes,
        ocr_polys,
        float(signal.get("width", 0)),
        float(signal.get("height", 0)),
    )
    analysis["ocr"] = {
        "status": ocr_status,
        "success": bool(getattr(ocr, "success", False)),
        "line_count": int(len(ocr_lines)),
        "avg_text_conf": round(ocr_avg, 4),
        "text_char_count": int(len(ocr_text)),
        "text_area_ratio": round(text_area_ratio, 4),
        "input_bytes": int(getattr(ocr, "input_bytes", 0)),
        "reason": _text(ocr.reason),
    }

    package_slide = None
    if package:
        slides = package.get("slides") if isinstance(package.get("slides"), list) else []
        if isinstance(package_slide_index := _safe_int(slide.get("page")), int) and package.get("slides"):
            package_slide = next(
                (
                    item
                    for item in slides
                    if isinstance(item, Mapping) and _safe_int(item.get("page")) == package_slide_index
                ),
                None,
            )

    package_title = _candidate_title(package or {}) if isinstance(package, Mapping) else default_candidate_title
    account = _text(slide.get("account") or default_account)
    category = _text((package.get("candidate", {}).get("category") if isinstance(package, Mapping) else "") if package else "")
    package_category = _candidate_category(package or {})

    topics = _collect_topics(
        package or {},
        package_slide if isinstance(package_slide, Mapping) else slide,
        package_title,
        account,
        category or package_category,
    )

    if not topics:
        topics = [package_title, package_category, account] if any([package_title, package_category, account]) else ["CardNews slide"]

    cached_openclip = (
        cached_model_evidence.get("openclip_result")
        if isinstance(cached_model_evidence, Mapping)
        and isinstance(cached_model_evidence.get("openclip_result"), Mapping)
        else None
    )
    if cached_openclip is not None:
        openclip_result = deepcopy(dict(cached_openclip))
    else:
        try:
            openclip_result = openclip_runtime.score_image_topics(
                image_path,
                topics,
                timeout_seconds=openclip_timeout,
            )
        except Exception as exc:  # pragma: no cover - defensive
            openclip_result = {
                "status": "failed",
                "passed": False,
                "reason": f"{type(exc).__name__}:{exc}",
                "ranked_topics": [],
                "runtime_probe": {"ready": False},
            }
    if model_evidence_capture is not None:
        model_evidence_capture["ocr"] = {
            "status": ocr_status,
            "text": ocr_text,
            "lines": deepcopy(ocr_lines),
            "boxes": deepcopy(list(ocr_boxes)),
            "polys": deepcopy(list(ocr_polys)),
            "scores": deepcopy(ocr_scores),
            "success": bool(getattr(ocr, "success", False)),
            "input_bytes": int(getattr(ocr, "input_bytes", 0)),
            "reason": _text(getattr(ocr, "reason", "")),
        }
        model_evidence_capture["openclip_result"] = deepcopy(
            dict(openclip_result)
        )

    analysis["openclip"] = {
        "status": _text(openclip_result.get("status")),
        "reason": _text(openclip_result.get("reason")),
        "runtime_ready": bool(openclip_result.get("runtime_probe", {}).get("ready")),
    }
    ranked = openclip_result.get("ranked_topics") if isinstance(openclip_result.get("ranked_topics"), list) else []
    if ranked:
        best = ranked[0]
        analysis["openclip"]["best"] = {
            "topic": _text(best.get("topic")),
            "cosine_similarity": round(_to_float(best.get("cosine_similarity")), 6),
        }
        best_score = _to_float(best.get("cosine_similarity"))
    else:
        best_score = 0.0
    metrics["openclip_best_score"] = round(best_score, 6)

    media_type = _text(slide.get("media_type")).lower()
    is_detail = bool(
        _safe_int(slide.get("page")) > 1
        or (
            isinstance(package_slide, Mapping)
            and _text(package_slide.get("role")).lower()
            not in {"", "cover", "hook", "opening"}
        )
    )
    has_media = _package_slide_has_media(
        package_slide if isinstance(package_slide, Mapping) else None,
        slide,
    )
    openclip_topic_pass = bool(
        openclip_result.get("passed") is True or best_score >= 0.195
    )
    media_topic_primary = bool(has_media and non_blank and openclip_topic_pass)
    image_is_primary = bool(
        media_type == "editorial"
        or text_area_ratio < IMAGE_IS_PRIMARY_AREA_THRESHOLD
        or media_topic_primary
    )
    analysis["image_primary_evidence"] = {
        "passed": image_is_primary,
        "media_type": media_type,
        "source_media_present": has_media,
        "visual_signal_non_blank": non_blank,
        "openclip_topic_pass": openclip_topic_pass,
        "text_area_ratio": round(text_area_ratio, 4),
        "text_area_threshold": IMAGE_IS_PRIMARY_AREA_THRESHOLD,
        "media_topic_primary": media_topic_primary,
    }
    expected_copy = ""
    if isinstance(package_slide, Mapping):
        expected_copy = " ".join(
            filter(
                None,
                (
                    _text(package_slide.get("headline")),
                    _text(package_slide.get("body")),
                ),
            )
        )
    copy_text = ocr_text
    copy_lines = ocr_lines
    copy_boxes = ocr_boxes
    copy_polys = ocr_polys
    copy_scores = ocr_scores
    copy_text_area_ratio = text_area_ratio
    copy_measurement_scope = "all_ocr_text"
    excluded_source_ocr_line_count = 0
    if has_media and _is_source_media_lower_third(
        package_slide if isinstance(package_slide, Mapping) else None
    ):
        overlay_indexes = _lower_third_expected_overlay_indexes(
            ocr_lines,
            ocr_boxes,
            ocr_polys,
            expected_copy,
            float(signal.get("height", 0)),
        )
        copy_lines = [
            ocr_lines[index]
            for index in overlay_indexes
            if index < len(ocr_lines)
        ]
        copy_text = " ".join(_text(line) for line in copy_lines if _text(line))
        copy_boxes = [
            ocr_boxes[index]
            for index in overlay_indexes
            if index < len(ocr_boxes)
        ]
        copy_polys = [
            ocr_polys[index]
            for index in overlay_indexes
            if index < len(ocr_polys)
        ]
        copy_scores = [
            ocr_scores[index]
            for index in overlay_indexes
            if index < len(ocr_scores)
        ]
        copy_text_area_ratio = _text_area_ratio(
            copy_boxes,
            copy_polys,
            float(signal.get("width", 0)),
            float(signal.get("height", 0)),
        )
        copy_measurement_scope = "source_media_lower_third_expected_overlay"
        excluded_source_ocr_line_count = max(
            0, len(ocr_lines) - len(copy_lines)
        )

    # Density and readability use rendered overlay copy for source-media
    # lower-third cards. Raw OCR remains available for evidence and strict
    # detail/no-media checks.
    copy_density_ok = (len(copy_text) <= 260) and (len(copy_lines) <= 12)
    copy_ocr_avg = (
        sum(copy_scores) / len(copy_scores) if copy_scores else 0.0
    )
    copy_integrity = _copy_integrity(
        package_slide if isinstance(package_slide, Mapping) else None,
        copy_text,
        copy_lines,
        ocr_success=bool(getattr(ocr, "success", False)),
        ocr_status=ocr_status,
    )
    analysis["copy_measurement"] = {
        "scope": copy_measurement_scope,
        "raw_text_char_count": len(ocr_text),
        "raw_line_count": len(ocr_lines),
        "raw_text_area_ratio": round(text_area_ratio, 4),
        "effective_text_char_count": len(copy_text),
        "effective_line_count": len(copy_lines),
        "effective_text_area_ratio": round(copy_text_area_ratio, 4),
        "effective_avg_text_conf": round(copy_ocr_avg, 4),
        "excluded_source_ocr_line_count": excluded_source_ocr_line_count,
    }
    expected_copy_only = bool(has_media)
    geometry_safety = _ocr_geometry_safety(
        copy_boxes,
        copy_polys,
        float(signal.get("width", 0)),
        float(signal.get("height", 0)),
        ocr_lines=copy_lines,
        expected_copy=expected_copy,
        expected_copy_only=expected_copy_only,
    )
    analysis["copy_integrity"] = copy_integrity
    analysis["layout_safety"] = geometry_safety
    copy_readability = bool(
        (copy_text or non_blank)
        and copy_integrity["passed"]
        and geometry_safety["passed"]
    )
    mobile_readability = bool(
        copy_text
        and (
            (ocr.success and copy_ocr_avg >= 0.28)
            or (len(copy_text) >= 20)
            or (len(copy_lines) >= 1 and ocr_status == "completed")
        )
        and geometry_safety["passed"]
    )
    content_readable = bool(ocr_text) and (len(ocr_text) >= 2)
    subject_focus = best_score >= 0.195
    subject_crop_preserved = non_blank
    template_crop_window = slide.get("template_crop_window")
    if template_crop_window is not None and not isinstance(template_crop_window, Mapping):
        template_crop_window = None

    subject_crop_metric: Dict[str, Any] = {
        "status": "subject_crop_evaluation_pending",
    }
    subject_bbox = _read_subject_bbox_from_image(image_path)
    if subject_bbox.get("status") == "ok" and isinstance(subject_bbox.get("primary_bbox"), Mapping):
        source_size = (
            int(analysis["visual_signal"].get("width", 0)),
            int(analysis["visual_signal"].get("height", 0)),
        )
        if source_size[0] > 0 and source_size[1] > 0:
            subject_crop_metric = _evaluate_subject_crop_guard(
                subject_bbox["primary_bbox_xyxy"],
                source_size,
                template_crop_window=template_crop_window,
                max_subject_outside_ratio=SUBJECT_CROP_GUARD_MAX_SUBJECT_OUTSIDE_RATIO,
                metric_precision=SUBJECT_CROP_GUARD_METRIC_PRECISION,
            )
            subject_crop_preserved = bool(subject_crop_metric.get("subject_crop_pass"))
        else:
            subject_crop_metric["status"] = "source_size_invalid"
            subject_crop_metric["reason"] = "image_size_is_invalid"
            subject_crop_preserved = False
    elif "status" in subject_bbox:
        subject_crop_metric["status"] = _text(subject_bbox.get("status"))
        subject_crop_metric["reason"] = _text(subject_bbox.get("reason"))
        subject_crop_metric["rembg_detail"] = subject_bbox

    story_progression = bool(_safe_int(slide.get("page")) > 0)
    blankness_proxy = float(signal.get("blankness_proxy", 1.0))
    sparse_detail = bool(
        is_detail
        and blankness_proxy >= DETAIL_BLANKNESS_THRESHOLD
        and not has_media
        and text_area_ratio < DETAIL_TEXT_AREA_MIN
        and len(ocr_text) < DETAIL_TEXT_CHAR_MIN
        and len(ocr_lines) < DETAIL_TEXT_LINE_MIN
    )
    analysis["detail_blankness"] = {
        "passed": not sparse_detail,
        "is_detail": is_detail,
        "has_media": has_media,
        "blankness_proxy": round(blankness_proxy, 4),
        "blankness_threshold": DETAIL_BLANKNESS_THRESHOLD,
        "text_area_ratio": round(text_area_ratio, 4),
        "minimum_text_area_ratio": DETAIL_TEXT_AREA_MIN,
        "text_char_count": len(ocr_text),
        "minimum_text_char_count": DETAIL_TEXT_CHAR_MIN,
        "line_count": len(ocr_lines),
        "minimum_line_count": DETAIL_TEXT_LINE_MIN,
        "reason_codes": (
            ["detail_high_blankness_with_insufficient_text_and_media"]
            if sparse_detail
            else []
        ),
    }

    findings["mobile_readability"] = PASS if mobile_readability else FAIL
    findings["copy_density_ok"] = PASS if copy_density_ok else FAIL
    findings["copy_readability"] = PASS if copy_readability else FAIL
    findings["image_is_primary"] = PASS if image_is_primary else FAIL
    findings["content_not_blank"] = (
        PASS
        if (content_readable or blankness_proxy < 0.07) and not sparse_detail
        else FAIL
    )
    findings["subject_focus"] = PASS if subject_focus else FAIL
    findings["subject_crop_preserved"] = PASS if subject_crop_preserved else FAIL
    findings["story_progression"] = PASS if story_progression else FAIL

    analysis["subject_crop_guard"] = subject_crop_metric

    return findings, analysis, metrics


def build_receipt_payload(
    manifest: Mapping[str, Any],
    *,
    candidate_filter: Iterable[str] | None,
    maker_id: str,
    reviewer_id: str,
    openclip_timeout: float,
    ocr_timeout: float,
    representative_receipt_ids: Mapping[str, Any] | None = None,
    feed_caption_by_candidate: Mapping[str, Any] | None = None,
    qa_cache_root: Path | None = None,
    max_workers: int = 3,
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    filter_set = {candidate.strip() for candidate in (candidate_filter or []) if str(candidate).strip()}
    expected = [row for row in _expected_slides(manifest) if row.get("candidate_id") in filter_set] if filter_set else _expected_slides(manifest)
    if filter_set and not expected:
        raise ValueError("No expected slide entries match the candidate filter")

    candidates = sorted({_text(row.get("candidate_id")) for row in expected})
    accounts = sorted({_text(row.get("account")) for row in expected})
    output_set_id = _text(manifest.get("output_set_id")) or _text(manifest.get("authorization_id")) or "unknown-output-set"
    reviewed_at = datetime.now(timezone.utc).isoformat()

    package_by_candidate = _load_packages(manifest, set(candidates))
    resolved_feed_caption_by_candidate = {
        candidate_id: caption
        for candidate_id in candidates
        if (
            caption := _candidate_feed_caption(
                candidate_id,
                package_by_candidate.get(candidate_id, {}),
                feed_caption_by_candidate,
            )
        )
    }
    openclip_runtime = OpenClipRuntime()
    openclip_probe = openclip_runtime.probe()
    openclip_ready = bool(openclip_probe.get("ready"))
    model_config = _visual_qa_model_config(
        openclip_probe,
        openclip_timeout=openclip_timeout,
        ocr_timeout=ocr_timeout,
    )
    cache_root = (
        Path(qa_cache_root)
        if qa_cache_root is not None
        else Path(
            os.getenv(
                "AI_CONTENT_OS_VISUAL_QA_CACHE_ROOT",
                str(DEFAULT_VISUAL_QA_CACHE_ROOT),
            )
        )
    )

    # PaddleOCR readiness is inferred from the first successful attempt path.
    ocr_ready = True

    slides_payload: list[dict[str, Any]] = []
    openclip_scores: list[float] = []
    cache_hits = 0
    cache_misses = 0

    def analyze_expected_row(
        row: Mapping[str, Any],
    ) -> tuple[
        Dict[str, str],
        Dict[str, Any],
        Dict[str, float],
        str,
        bool,
    ]:
        candidate_id = _text(row.get("candidate_id"))
        page = _safe_int(row.get("page"))
        image_path = Path(_text(row.get("image_path")))
        package = package_by_candidate.get(candidate_id, {})
        package_slides = (
            package.get("slides")
            if isinstance(package, Mapping)
            and isinstance(package.get("slides"), list)
            else []
        )
        package_slide = next(
            (
                slide
                for slide in package_slides
                if isinstance(slide, Mapping)
                and _safe_int(slide.get("page")) == page
            ),
            {},
        )
        expected_copy = " ".join(
            filter(
                None,
                (
                    _text(package_slide.get("headline")),
                    _text(package_slide.get("body")),
                ),
            )
        )
        image_sha256 = _sha256(image_path) if image_path.is_file() else ""
        semantic_context = {
            "candidate_title": _candidate_title(package),
            "candidate_category": _candidate_category(package),
            "account": _text(row.get("account")),
        }
        cache_key = _visual_qa_cache_key(
            image_sha256=image_sha256,
            expected_copy=expected_copy,
            semantic_context=semantic_context,
            config_hash=_text(model_config.get("config_hash")),
        )
        cache_path = cache_root / cache_key[:2] / f"{cache_key}.json"
        cached_evidence = _load_visual_qa_model_cache(
            cache_path,
            cache_key=cache_key,
            config_hash=_text(model_config.get("config_hash")),
        )
        captured_evidence: Dict[str, Any] = {}
        findings, analysis, metric = _analyze_slide(
            row,
            package,
            openclip_runtime=(
                openclip_runtime
                if cached_evidence is not None
                else OpenClipRuntime()
            ),
            openclip_timeout=openclip_timeout,
            ocr_timeout=ocr_timeout,
            default_account=_text(row.get("account")),
            default_candidate_title=_candidate_title(package),
            cached_model_evidence=cached_evidence,
            model_evidence_capture=captured_evidence,
        )
        cache_hit = cached_evidence is not None
        if not cache_hit:
            _write_visual_qa_model_cache(
                cache_path,
                cache_key=cache_key,
                config=model_config,
                image_sha256=image_sha256,
                expected_copy=expected_copy,
                model_evidence=captured_evidence,
            )
        analysis["model_cache"] = {
            "status": "hit" if cache_hit else "miss",
            "schema_version": VISUAL_QA_MODEL_CACHE_SCHEMA,
            "config_hash": _text(model_config.get("config_hash")),
            "cache_key": cache_key,
            "failure_cache_used": False,
        }
        return findings, analysis, metric, image_sha256, cache_hit

    analyzed_rows = _bounded_ordered_map(
        expected,
        analyze_expected_row,
        max_workers=max_workers,
    )
    for row, analyzed in zip(expected, analyzed_rows):
        candidate_id = _text(row.get("candidate_id"))
        page = int(row.get("page", 0) or 0)
        image_path = Path(_text(row.get("image_path")))
        package = package_by_candidate.get(candidate_id, {})
        candidate_candidate = package.get("candidate") if isinstance(package, Mapping) else None
        account = _text(row.get("account"))
        if isinstance(candidate_candidate, Mapping):
            account = account or _text(candidate_candidate.get("account"))

        default_category = _text(package.get("candidate", {}).get("category") if isinstance(package, Mapping) else "")

        findings, analysis, metric, image_sha256, cache_hit = analyzed
        if cache_hit:
            cache_hits += 1
        else:
            cache_misses += 1

        if row.get("requires_comment_readability"):
            ocr_status = _text(analysis.get("ocr", {}).get("status"))
            ocr_line_count = _safe_int(analysis.get("ocr", {}).get("line_count", 0))
            ocr_success = bool(analysis.get("ocr", {}).get("success"))
            comment_ok = ocr_success and ocr_status == "completed" and ocr_line_count >= 1
            findings["comment_readability"] = PASS if comment_ok else FAIL
        else:
            findings["comment_readability"] = NOT_APPLICABLE
        feed_caption_present = bool(
            _text(resolved_feed_caption_by_candidate.get(candidate_id))
        )
        findings["feed_caption_present"] = (
            PASS if feed_caption_present else FAIL
        )
        analysis["metadata_binding"] = {
            "candidate_id": candidate_id,
            "feed_caption_map_key_found": (
                candidate_id in resolved_feed_caption_by_candidate
            ),
            "feed_caption_present": feed_caption_present,
        }

        if any(value not in {PASS, NOT_APPLICABLE, FAIL} for value in findings.values()):
            raise RuntimeError("finding must be pass/not_applicable/fail")
        for required in REQUIRED_FINDINGS:
            findings.setdefault(required, FAIL)

        slide_payload = {
            "candidate_id": candidate_id,
            "page": page,
            "image_path": str(image_path),
            "image_sha256": image_sha256,
            "analysis_contract": {
                "source": "pixel_contract",
                "openclip_ready": openclip_ready,
                "paddleocr_ready": ocr_ready,
                "openclip_timeout_seconds": openclip_timeout,
                "ocr_timeout_seconds": ocr_timeout,
            },
            "findings": findings,
            "analysis": analysis,
        }
        if _text(analysis.get("visual_signal", {}).get("width")):
            slide_payload["width"] = _safe_int(analysis["visual_signal"].get("width"))
            slide_payload["height"] = _safe_int(analysis["visual_signal"].get("height"))

        slides_payload.append(slide_payload)
        for key, value in metric.items():
            openclip_scores.append(_to_float(value))

    scope = _receipt_scope(candidates, accounts, representative_receipt_ids)

    receipt = {
        "schema_version": "cardnews_visual_qa_receipt_v1",
        "receipt_id": f"visual-qa-{output_set_id}-representative",
        "approval_kind": "automatic_visual_evidence",
        "owner_visual_approval": False,
        "owner_approved_by": None,
        "evidence_only": True,
        "automatic_evidence_only": True,
        "output_set_id": output_set_id,
        "reviewed_at": reviewed_at,
        "maker": {"id": maker_id},
        "reviewer": {"id": reviewer_id, "role": "automated_qa", "independent_from_maker": True},
        "scope": scope,
        "decision": "evidence_only",
        "slides": slides_payload,
        "analysis_contract": {
            "openclip_ready": openclip_ready,
            "paddleocr_ready": ocr_ready,
            "openclip_timeout_seconds": openclip_timeout,
            "ocr_timeout_seconds": ocr_timeout,
            "openclip_probe": openclip_probe,
            "model_cache_schema": VISUAL_QA_MODEL_CACHE_SCHEMA,
            "model_cache_config_hash": _text(model_config.get("config_hash")),
            "max_workers": max(
                1,
                min(int(max_workers), MAX_VISUAL_QA_WORKERS),
            ),
        },
    }
    if len(candidates) == 1:
        receipt["feed_caption"] = _text(
            resolved_feed_caption_by_candidate.get(candidates[0])
        )
    else:
        receipt["feed_caption_by_candidate"] = dict(
            resolved_feed_caption_by_candidate
        )

    final_receipt, assessed = _assess_final_receipt(
        receipt,
        expected,
        output_set_id=output_set_id,
        scope=scope,
    )
    final_slides = (
        final_receipt.get("slides")
        if isinstance(final_receipt.get("slides"), list)
        else []
    )
    metrics = {
        "candidate_count": len(candidates),
        "slide_count": len(final_slides),
        "openclip_best_scores": openclip_scores,
        "model_cache_hits": cache_hits,
        "model_cache_misses": cache_misses,
    }
    return final_receipt, assessed, metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--candidate-id", action="append", default=None)
    parser.add_argument("--maker-id", default="cardnews-renderer")
    parser.add_argument("--reviewer-id", default="independent-visual-qa-auto")
    parser.add_argument("--openclip-timeout", type=float, default=30.0)
    parser.add_argument("--ocr-timeout", type=float, default=30.0)
    parser.add_argument("--qa-cache-root", type=Path)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    manifest = _read_json(args.manifest)
    if not isinstance(manifest, Mapping):
        raise RuntimeError("manifest must be an object")

    candidate_filter = args.candidate_id if args.candidate_id else None
    receipt, assessed, metrics = build_receipt_payload(
        manifest,
        candidate_filter=candidate_filter,
        maker_id=args.maker_id.strip(),
        reviewer_id=args.reviewer_id.strip(),
        openclip_timeout=args.openclip_timeout,
        ocr_timeout=args.ocr_timeout,
        qa_cache_root=args.qa_cache_root,
        max_workers=args.max_workers,
    )
    receipt_passed = bool(assessed.get("visual_qa_passed"))
    receipt["decision"] = "evidence_only" if receipt_passed else "blocked"

    output = {
        "qa_receipt": receipt,
        "qa_assessment": assessed,
        "analysis_summary": {
            "decision": assessed.get("status"),
            "passed": bool(assessed.get("visual_qa_passed")),
            "failure_count": int(assessed.get("failure_count", 0)),
            "openclip_scores": metrics.get("openclip_best_scores", []),
            "candidate_count": int(metrics.get("candidate_count", 0)),
            "slide_count": int(metrics.get("slide_count", 0)),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output["qa_receipt"], ensure_ascii=False, indent=2 if args.pretty else None),
        encoding="utf-8",
    )
    print(f"written: {args.output}")
    print(json.dumps(output["qa_assessment"], ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

