"""Single fail-closed entry point for CardNews production control.

This command controls receipts and authorization only.  It does not publish,
issue affiliate links, resume automation, or silently approve rendered media.
Actual rendering remains a separate controller-authorized subprocess and its
outputs cannot become manual-upload-ready before independent visual QA.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from modules.agent_console.package_completion_gate import assess_package_completion
from modules.card_news.production_controller import (
    ACCEPT_BATCH_QA,
    ACCEPT_REPRESENTATIVE_QA,
    AUTHORIZE_BATCH,
    AUTHORIZE_REPRESENTATIVES,
    BATCH_AUTHORIZED,
    BIND_HARD_RULES,
    RECORD_BATCH_RENDER,
    RECORD_REPRESENTATIVE_RENDER,
    REPRESENTATIVE_AUTHORIZED,
    REQUIRED_HARD_RULE_IDS,
    ProductionControllerError,
    apply_transition,
    build_transition_receipt,
    canonical_hash,
    initialize_controller,
    validate_state,
)
from modules.card_news.visual_qa_gate import assess_visual_qa_receipt
from modules.tool_adapters.cardnews_renderer_runtime import (
    DEFAULT_RENDER_TIMEOUT_SECONDS,
    MAX_RENDER_TIMEOUT_SECONDS,
    CardNewsRendererRuntime,
)
from scripts.render_selected_cardnews_preupload import _fragment_digest


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIRECTIVES = REPO_ROOT / "knowledge" / "owner_directives" / "cardnews_owner_directives.json"
SUBJECT_CROP_GUARD_POLICY_VERSION = "subject_crop_guard_template_frame_v1"
SUBJECT_CROP_GUARD_POLICY_MODE = "template_crop_subject_loss"
SUBJECT_CROP_GUARD_SCOPE = "template_frame_only"
SUBJECT_CROP_GUARD_FRAME_PROFILE = "instagram_portrait_1080x1350"
SUBJECT_CROP_GUARD_BBOX_SOURCE = "rembg_alpha_v1"
SUBJECT_CROP_GUARD_MAX_SUBJECT_OUTSIDE_RATIO = 0.06
SUBJECT_CROP_GUARD_MIN_SUBJECT_KEPT_RATIO = 0.94
SUBJECT_CROP_GUARD_METRIC_PRECISION = 4
SUBJECT_CROP_GUARD_REASON_PREFIX = "template_crop_subject_loss"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_float(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _to_xyxy(rect: Mapping[str, Any], *, width: float, height: float) -> tuple[float, float, float, float] | None:
    if not isinstance(rect, Mapping):
        return None

    x = rect.get("x")
    y = rect.get("y")
    w = rect.get("width")
    h = rect.get("height")
    if all(isinstance(value, (int, float)) for value in (x, y, w, h)):
        return (float(x), float(y), float(x) + float(w), float(y) + float(h))

    x1 = rect.get("x1")
    y1 = rect.get("y1")
    x2 = rect.get("x2")
    y2 = rect.get("y2")
    if all(isinstance(value, (int, float)) for value in (x1, y1, x2, y2)):
        return (float(x1), float(y1), float(x2), float(y2))

    if all(isinstance(value, (int, float)) for value in (x, y, w, h)):
        normalized = all(0 <= _safe_float(v) <= 1 for v in (x, y, w, h))
        if normalized:
            return (float(x) * width, float(y) * height, float(x) * width + float(w) * width, float(y) * height + float(h) * height)

    return None


def _rect_area(rect: tuple[float, float, float, float]) -> float:
    x1, y1, x2, y2 = rect
    width = max(0.0, x2 - x1)
    height = max(0.0, y2 - y1)
    return width * height


def _intersection_area(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> float:
    x1 = max(first[0], second[0])
    y1 = max(first[1], second[1])
    x2 = min(first[2], second[2])
    y2 = min(first[3], second[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    return (x2 - x1) * (y2 - y1)


def _normalize_crop_window(
    window: Mapping[str, Any] | None,
    source_width: float,
    source_height: float,
) -> tuple[float, float, float, float]:
    if not window:
        return (0.0, 0.0, source_width, source_height)
    parsed = _to_xyxy(window, width=source_width, height=source_height)
    if parsed is None:
        return (0.0, 0.0, source_width, source_height)
    x1, y1, x2, y2 = parsed
    if source_width > 0:
        x1, x2 = max(0.0, min(source_width, x1)), max(0.0, min(source_width, x2))
    if source_height > 0:
        y1, y2 = max(0.0, min(source_height, y1)), max(0.0, min(source_height, y2))
    if x2 <= x1 or y2 <= y1:
        return (0.0, 0.0, source_width, source_height)
    return (x1, y1, x2, y2)


def _evaluate_subject_crop_guard(
    subject_bbox: Mapping[str, Any],
    source_size: tuple[int, int],
    *,
    template_size: tuple[int, int] = (1080, 1350),
    template_crop_window: Mapping[str, Any] | None = None,
    metric_precision: int = SUBJECT_CROP_GUARD_METRIC_PRECISION,
    max_subject_outside_ratio: float = SUBJECT_CROP_GUARD_MAX_SUBJECT_OUTSIDE_RATIO,
) -> Dict[str, Any]:
    source_width, source_height = source_size
    if source_width <= 0 or source_height <= 0:
        return {
            "status": "invalid_source_size",
            "source_size": {"width": source_width, "height": source_height},
            "subject_crop_outside_ratio": 1.0,
            "subject_crop_pass": False,
            "max_subject_outside_ratio": max_subject_outside_ratio,
            "template_frame": {"width": template_size[0], "height": template_size[1]},
            "metrics_precision": metric_precision,
        }

    subject = _to_xyxy(subject_bbox, width=source_width, height=source_height)
    if subject is None:
        return {
            "status": "invalid_subject_bbox",
            "subject_crop_outside_ratio": 1.0,
            "subject_crop_pass": False,
            "max_subject_outside_ratio": max_subject_outside_ratio,
            "template_frame": {"width": template_size[0], "height": template_size[1]},
            "metrics_precision": metric_precision,
        }

    source_crop = _normalize_crop_window(template_crop_window, source_width, source_height)
    subject_area = _rect_area(subject)
    if subject_area <= 0.0:
        return {
            "status": "invalid_subject_area",
            "subject_crop_outside_ratio": 1.0,
            "subject_crop_pass": False,
            "max_subject_outside_ratio": max_subject_outside_ratio,
            "template_frame": {"width": template_size[0], "height": template_size[1]},
            "metrics_precision": metric_precision,
        }

    kept_subject_area = _intersection_area(subject, source_crop)
    subject_outside_ratio = (subject_area - kept_subject_area) / subject_area

    source_crop_width = max(1e-9, source_crop[2] - source_crop[0])
    source_crop_height = max(1e-9, source_crop[3] - source_crop[1])

    kept_x1, kept_y1, kept_x2, kept_y2 = (
        max(subject[0], source_crop[0]),
        max(subject[1], source_crop[1]),
        min(subject[2], source_crop[2]),
        min(subject[3], source_crop[3]),
    )
    subject_for_template_projection = (
        (subject[0] - source_crop[0]) * 1.0,
        (subject[1] - source_crop[1]) * 1.0,
        (subject[2] - source_crop[0]) * 1.0,
        (subject[3] - source_crop[1]) * 1.0,
    )
    template_width, template_height = template_size
    scale = min(template_width / source_crop_width, template_height / source_crop_height)
    offset_x = (template_width - source_crop_width * scale) / 2.0
    offset_y = (template_height - source_crop_height * scale) / 2.0

    projected_subject = (
        subject_for_template_projection[0] * scale + offset_x,
        subject_for_template_projection[1] * scale + offset_y,
        subject_for_template_projection[2] * scale + offset_x,
        subject_for_template_projection[3] * scale + offset_y,
    )
    template_crop_area = (
        offset_x,
        offset_y,
        offset_x + source_crop_width * scale,
        offset_y + source_crop_height * scale,
    )
    frame_kept_area = _intersection_area(projected_subject, template_crop_area)
    projected_subject_area = _rect_area(projected_subject)
    outside_ratio_in_frame = (
        1.0 - (frame_kept_area / projected_subject_area if projected_subject_area else 0.0)
    ) if projected_subject_area > 0 else 1.0

    status = "pass" if outside_ratio_in_frame <= max_subject_outside_ratio else "fail"
    precision = metric_precision if metric_precision >= 0 else 0
    return {
        "status": status,
        "max_subject_outside_ratio": round(max_subject_outside_ratio, precision),
        "subject_crop_outside_ratio": round(subject_outside_ratio, precision),
        "subject_crop_outside_ratio_in_template_frame": round(outside_ratio_in_frame, precision),
        "subject_area": int(subject_area),
        "kept_subject_area": round(kept_subject_area, precision),
        "source_crop_window": {
            "x1": round(source_crop[0], precision),
            "y1": round(source_crop[1], precision),
            "x2": round(source_crop[2], precision),
            "y2": round(source_crop[3], precision),
        },
        "template_frame": {
            "width": template_size[0],
            "height": template_size[1],
        },
        "projected_subject_bbox": {
            "x1": round(projected_subject[0], precision),
            "y1": round(projected_subject[1], precision),
            "x2": round(projected_subject[2], precision),
            "y2": round(projected_subject[3], precision),
        },
        "subject_crop_pass": outside_ratio_in_frame <= max_subject_outside_ratio,
    }


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _atomic_create(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError as exc:
        raise ProductionControllerError(
            "render_authorization_consumption_exists", str(path)
        ) from exc
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())


def _adapter_consumption_path(authorization: Mapping[str, Any]) -> Path:
    output_root = Path(_text(authorization.get("output_root")))
    authorization_id = _text(authorization.get("authorization_id"))
    if not output_root.is_absolute() or not authorization_id:
        raise ProductionControllerError(
            "render_authorization_consumption_invalid",
            "authorization needs an absolute output root and authorization id",
        )
    return output_root.parent / ".controller_authorizations" / f"{authorization_id}.consumed.json"


def _load_packages(path: Path) -> List[Mapping[str, Any]]:
    payload = _read_json(path)
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, Mapping):
        rows = payload.get("packages")
        if not isinstance(rows, list):
            rows = payload.get("records")
        if not isinstance(rows, list):
            rows = [payload]
    else:
        rows = []
    packages = [row for row in rows if isinstance(row, Mapping)]
    if not packages:
        raise ProductionControllerError("packages_missing", "package file contains no package objects")
    return packages


def _load_state(path: Path) -> Dict[str, Any]:
    state = _read_json(path)
    validate_state(state)
    return dict(state)


def _hard_rules(path: Path) -> List[Dict[str, str]]:
    payload = _read_json(path)
    by_id = {
        _text(row.get("claim_id")): row
        for row in payload.get("directives", [])
        if isinstance(row, Mapping) and row.get("owner_approved") is True
    }
    rows: List[Dict[str, str]] = []
    for claim_id in REQUIRED_HARD_RULE_IDS:
        row = by_id.get(claim_id)
        if not row or not _text(row.get("rule")):
            raise ProductionControllerError("hard_rule_missing", f"{claim_id} is not owner-approved and complete")
        rows.append({"claim_id": claim_id, "rule": _text(row.get("rule")), "source": str(path.resolve())})
    return rows


def _apply(state_path: Path, transition: str, receipt_id: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
    state = _load_state(state_path)
    receipt = build_transition_receipt(state, transition, receipt_id, payload)
    updated = apply_transition(state, receipt)
    _atomic_write(state_path, updated)
    return updated


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _render_receipts(manifest: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    receipts: Dict[str, Dict[str, Any]] = {}
    for record in manifest.get("records", []):
        if not isinstance(record, Mapping) or record.get("status") != "render_completed_pending_visual_qa":
            continue
        candidate_id = _text(record.get("candidate_id"))
        outputs = [Path(value) for value in record.get("outputs", []) if _text(value)]
        if not candidate_id or not outputs or any(not path.is_file() for path in outputs):
            continue
        output_hashes = {_text(str(path)): _sha256(path) for path in outputs}
        receipts[candidate_id] = {
            "candidate_id": candidate_id,
            "status": "render_completed_pending_visual_qa",
            "expected_slide_count": len(outputs),
            "rendered_slide_count": len(outputs),
            "output_hashes": output_hashes,
            "manifest_schema_version": _text(manifest.get("schema_version")),
            "authorization_id": _text(manifest.get("authorization_id")),
            "output_set_id": _text(manifest.get("output_set_id")),
            "controller_state_hash": _text(manifest.get("controller_state_hash")),
            "batch_hash": _text(manifest.get("batch_hash")),
            "hard_rule_hash": _text(manifest.get("hard_rule_hash")),
            "authorization_id": _text(manifest.get("authorization_id")),
            "render_mode": _text(manifest.get("render_mode")),
            "local_media_binding_hash": _text(manifest.get("local_media_binding_hash")),
        }
    return receipts


def _is_comment_slide(slide: Mapping[str, Any]) -> bool:
    material = " ".join(
        _text(slide.get(key)).lower() for key in ("role", "media", "media_type")
    )
    return "comment" in material or "댓글" in material


def _selected_comment_crops(package: Mapping[str, Any]) -> List[Dict[str, Any]]:
    evidence = (
        package.get("real_comment_evidence")
        if isinstance(package.get("real_comment_evidence"), Mapping)
        else {}
    )
    selected = evidence.get("selected") if isinstance(evidence, Mapping) else None
    if not isinstance(selected, list):
        selected = []
    return [dict(item) for item in selected if isinstance(item, Mapping)]


def _comment_crop_expected_hash(comment: Mapping[str, Any]) -> str:
    for key in ("screenshot_sha256", "image_sha256", "sha256", "hash"):
        value = _text(comment.get(key))
        if value:
            return value
    return ""


def _comment_crop_from_slide(
    slide: Mapping[str, Any],
    selected: Sequence[Mapping[str, Any]],
    fallback_index: int,
) -> Optional[Dict[str, Any]]:
    hints = [_text(slide.get(key)) for key in ("screenshot_path", "local_path", "asset_path", "image_path")]
    media = _text(slide.get("media"))
    if media:
        hints.append(media)
    for hint in [value for value in hints if value]:
        lower_hint = hint.lower()
        for comment in selected:
            raw_path = _text(comment.get("screenshot_path"))
            if not raw_path:
                continue
            lower_raw = raw_path.lower()
            if hint == raw_path or Path(hint).name == Path(raw_path).name:
                return dict(comment)
            if lower_raw in lower_hint:
                return dict(comment)
            if Path(raw_path).stem.lower() in lower_hint:
                return dict(comment)
    if 0 < fallback_index <= len(selected):
        return dict(selected[fallback_index - 1])
    return None


def _validate_subject_crop_guard(tooling: Mapping[str, Any]) -> Dict[str, Any]:
    guard = tooling.get("subject_crop_guard")
    if not isinstance(guard, Mapping):
        raise ProductionControllerError(
            "render_authorization_subject_crop_guard_missing",
            "subject_crop_guard block is required in tooling_authorization",
        )
    if (
        guard.get("enabled") is not True
        or _text(guard.get("policy_version")) != SUBJECT_CROP_GUARD_POLICY_VERSION
        or _text(guard.get("version")) != SUBJECT_CROP_GUARD_POLICY_VERSION
        or _text(guard.get("scope")) != SUBJECT_CROP_GUARD_SCOPE
        or _text(guard.get("mode")) != SUBJECT_CROP_GUARD_POLICY_MODE
        or _text(guard.get("frame_profile")) != SUBJECT_CROP_GUARD_FRAME_PROFILE
        or _text(guard.get("bbox_source")) != SUBJECT_CROP_GUARD_BBOX_SOURCE
        or _text(guard.get("reason_prefix")) != SUBJECT_CROP_GUARD_REASON_PREFIX
    ):
        raise ProductionControllerError(
            "render_authorization_subject_crop_guard_invalid",
            "subject_crop_guard policy/version/scope settings must match runtime requirements",
        )
    max_ratio_raw = guard.get("max_subject_outside_ratio")
    min_ratio_raw = guard.get("min_subject_kept_ratio")
    try:
        max_ratio = float(max_ratio_raw)
        min_ratio = float(min_ratio_raw)
    except (TypeError, ValueError) as exc:
        raise ProductionControllerError(
            "render_authorization_subject_crop_guard_invalid",
            "subject_crop_guard thresholds must be numeric",
        ) from exc
    if not 0 <= max_ratio <= 1 or not 0 <= min_ratio <= 1:
        raise ProductionControllerError(
            "render_authorization_subject_crop_guard_invalid",
            "subject_crop_guard thresholds must be in [0, 1]",
        )
    if abs(max_ratio - SUBJECT_CROP_GUARD_MAX_SUBJECT_OUTSIDE_RATIO) > 0.0001:
        raise ProductionControllerError(
            "render_authorization_subject_crop_guard_invalid",
            "subject_crop_guard.max_subject_outside_ratio has changed",
        )
    if abs(min_ratio - SUBJECT_CROP_GUARD_MIN_SUBJECT_KEPT_RATIO) > 0.0001:
        raise ProductionControllerError(
            "render_authorization_subject_crop_guard_invalid",
            "subject_crop_guard.min_subject_kept_ratio has changed",
        )
    metric_precision = guard.get("metric_precision")
    if not isinstance(metric_precision, int) or metric_precision < 0:
        raise ProductionControllerError(
            "render_authorization_subject_crop_guard_invalid",
            "subject_crop_guard.metric_precision must be a non-negative integer",
        )
    if metric_precision != SUBJECT_CROP_GUARD_METRIC_PRECISION:
        raise ProductionControllerError(
            "render_authorization_subject_crop_guard_invalid",
            "subject_crop_guard.metric_precision has changed",
        )
    return dict(guard)


def _validate_comment_slide_contract(
    candidate_id: str,
    slides: List[Mapping[str, Any]],
    package: Mapping[str, Any],
) -> None:
    selected = _selected_comment_crops(package)
    if not selected:
        for slide in slides:
            if _is_comment_slide(slide):
                raise ProductionControllerError(
                    "visual_qa_comment_crop_missing",
                    f"{candidate_id} has comment slide content but no comment evidence in package",
                )
        return
    comment_order = 0
    for slide in slides:
        if not _is_comment_slide(slide):
            continue
        comment_order += 1
        comment = _comment_crop_from_slide(slide, selected, comment_order)
        if not comment:
            raise ProductionControllerError(
                "visual_qa_comment_crop_missing",
                f"{candidate_id} comment slide has no matching comment crop in real_comment_evidence",
            )
        if comment.get("comment_slide_eligible") is not True:
            raise ProductionControllerError(
                "visual_qa_comment_slide_ineligible",
                f"{candidate_id} uses a comment crop marked comment_slide_eligible=False",
            )


def _coerce_template_crop_window(
    value: Any,
) -> Dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    prepared: Dict[str, Any] = {}
    for key in ("x", "y", "width", "height", "x1", "y1", "x2", "y2"):
        if key in value:
            prepared[key] = value[key]
    if not prepared:
        return None
    return prepared


def _validate_render_authorization(
    authorization: Any,
    manifest: Mapping[str, Any],
    state: Mapping[str, Any],
) -> Dict[str, Any]:
    """Bind record-render to the exact live authorization issued by this CLI."""

    if not isinstance(authorization, Mapping) or authorization.get("authorized") is not True:
        raise ProductionControllerError("render_authorization_missing", "issued authorization is required")
    token = dict(authorization)
    if _text(token.get("schema_version")) != "cardnews_render_authorization_v1":
        raise ProductionControllerError("render_authorization_schema_invalid", "unsupported authorization")
    authorization_id = _text(token.get("authorization_id"))
    unhashed = dict(token)
    unhashed.pop("authorization_id", None)
    expected_id = f"render-{canonical_hash(unhashed)[:24]}"
    if not authorization_id or authorization_id != expected_id:
        raise ProductionControllerError("render_authorization_tampered", "authorization id does not match token")
    if authorization_id in state.get("used_render_authorization_ids", []):
        raise ProductionControllerError("render_authorization_reused", authorization_id)
    try:
        expiry = datetime.fromisoformat(_text(token.get("expires_at")))
    except ValueError as exc:
        raise ProductionControllerError("render_authorization_expiry_invalid", "valid expires_at required") from exc
    if expiry.tzinfo is None or datetime.now().astimezone() >= expiry:
        raise ProductionControllerError("render_authorization_expired", authorization_id)
    mode = _text(token.get("mode"))
    expected_state = REPRESENTATIVE_AUTHORIZED if mode == "representative" else BATCH_AUTHORIZED
    if mode not in {"representative", "batch"} or state.get("state") != expected_state:
        raise ProductionControllerError("render_authorization_state_mismatch", mode or "missing mode")
    expected_candidates = (
        sorted(state.get("representatives", {}).values())
        if mode == "representative"
        else sorted(state.get("candidate_ids", []))
    )
    token_candidates = sorted({_text(item) for item in token.get("candidate_ids", []) if _text(item)})
    if token_candidates != expected_candidates:
        raise ProductionControllerError("render_authorization_scope_mismatch", "candidate scope changed")
    if (
        _text(token.get("controller_state_hash")) != state["state_hash"]
        or _text(token.get("controller_id")) != state["controller_id"]
        or _text(token.get("hard_rule_hash")) != state["hard_rule_hash"]
        or _text(token.get("batch_hash")) != state["batch_hash"]
    ):
        raise ProductionControllerError("render_authorization_binding_mismatch", "controller binding changed")
    expected_media = {
        candidate_id: list(state["local_media_receipt_hashes"][candidate_id])
        for candidate_id in expected_candidates
    }
    if token.get("local_media_receipt_hashes") != expected_media or _text(
        token.get("local_media_binding_hash")
    ) != canonical_hash(expected_media):
        raise ProductionControllerError("render_authorization_media_mismatch", "local-media binding changed")
    tooling = token.get("tooling_authorization") if isinstance(token.get("tooling_authorization"), Mapping) else {}
    if (
        tooling.get("renderer") is not True
        or tooling.get("satori") is not True
        or tooling.get("resvg") is not True
        or tooling.get("fabric") is not False
        or tooling.get("motion") is not False
        or tooling.get("scope") != mode
        or tooling.get("authorization_metadata_only") is not True
        or tooling.get("execution_performed") is not False
    ):
        raise ProductionControllerError(
            "render_authorization_tooling_invalid",
            "only the bounded Satori/resvg adapter is authorized",
        )
    _validate_subject_crop_guard(tooling)
    manifest_candidates = sorted({
        _text(row.get("candidate_id")) for row in manifest.get("records", [])
        if isinstance(row, Mapping) and _text(row.get("candidate_id"))
    })
    if manifest_candidates != expected_candidates:
        raise ProductionControllerError("render_manifest_scope_mismatch", "manifest candidate scope changed")
    expected_manifest = {
        "authorization_id": authorization_id,
        "output_set_id": authorization_id,
        "controller_state_hash": state["state_hash"],
        "batch_hash": state["batch_hash"],
        "hard_rule_hash": state["hard_rule_hash"],
        "render_mode": mode,
    }
    for field, expected in expected_manifest.items():
        if _text(manifest.get(field)) != expected:
            raise ProductionControllerError(
                "render_manifest_authorization_mismatch", f"manifest {field} does not match authorization"
            )
    return token


def _adapter_requests(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, Mapping) and isinstance(payload.get("requests"), list):
        rows = payload["requests"]
    elif isinstance(payload, Mapping):
        rows = [payload]
    else:
        rows = []
    requests = [dict(row) for row in rows if isinstance(row, Mapping)]
    if not requests or len(requests) != len(rows):
        raise ProductionControllerError(
            "renderer_adapter_request_invalid",
            "render-request JSON must be one object or an object containing only request objects",
        )
    return requests


def _validate_adapter_authorization(
    authorization: Any,
    state: Mapping[str, Any],
    requests: List[Mapping[str, Any]],
) -> Dict[str, Any]:
    if not isinstance(authorization, Mapping) or authorization.get("authorized") is not True:
        raise ProductionControllerError("render_authorization_missing", "issued authorization is required")
    token = dict(authorization)
    if _text(token.get("schema_version")) != "cardnews_render_authorization_v1":
        raise ProductionControllerError("render_authorization_schema_invalid", "unsupported authorization")
    authorization_id = _text(token.get("authorization_id"))
    unhashed = dict(token)
    unhashed.pop("authorization_id", None)
    if not authorization_id or authorization_id != f"render-{canonical_hash(unhashed)[:24]}":
        raise ProductionControllerError("render_authorization_tampered", "authorization id does not match token")
    if authorization_id in state.get("used_render_authorization_ids", []):
        raise ProductionControllerError("render_authorization_reused", authorization_id)
    try:
        expiry = datetime.fromisoformat(_text(token.get("expires_at")))
    except ValueError as exc:
        raise ProductionControllerError("render_authorization_expiry_invalid", "valid expires_at required") from exc
    if expiry.tzinfo is None or datetime.now().astimezone() >= expiry:
        raise ProductionControllerError("render_authorization_expired", authorization_id)

    mode = _text(token.get("mode"))
    expected_state = REPRESENTATIVE_AUTHORIZED if mode == "representative" else BATCH_AUTHORIZED
    if mode not in {"representative", "batch"} or state.get("state") != expected_state:
        raise ProductionControllerError("render_authorization_state_mismatch", mode or "missing mode")
    expected_candidates = (
        sorted(state.get("representatives", {}).values())
        if mode == "representative"
        else sorted(state.get("candidate_ids", []))
    )
    token_candidates = sorted({_text(value) for value in token.get("candidate_ids", []) if _text(value)})
    request_candidates = sorted({_text(row.get("candidate_id")) for row in requests if _text(row.get("candidate_id"))})
    if token_candidates != expected_candidates or request_candidates != expected_candidates or len(requests) != len(expected_candidates):
        raise ProductionControllerError(
            "render_authorization_scope_mismatch",
            "one bounded adapter request is required for every authorized candidate",
        )
    if (
        _text(token.get("controller_state_hash")) != state["state_hash"]
        or _text(token.get("controller_id")) != state["controller_id"]
        or _text(token.get("hard_rule_hash")) != state["hard_rule_hash"]
        or _text(token.get("batch_hash")) != state["batch_hash"]
    ):
        raise ProductionControllerError("render_authorization_binding_mismatch", "controller binding changed")
    expected_media = {
        candidate_id: list(state["local_media_receipt_hashes"][candidate_id])
        for candidate_id in expected_candidates
    }
    if token.get("local_media_receipt_hashes") != expected_media or _text(
        token.get("local_media_binding_hash")
    ) != canonical_hash(expected_media):
        raise ProductionControllerError("render_authorization_media_mismatch", "local-media binding changed")
    tooling = token.get("tooling_authorization") if isinstance(token.get("tooling_authorization"), Mapping) else {}
    if (
        tooling.get("renderer") is not True
        or tooling.get("satori") is not True
        or tooling.get("resvg") is not True
        or tooling.get("fabric") is not False
        or tooling.get("motion") is not False
        or tooling.get("scope") != mode
        or tooling.get("authorization_metadata_only") is not True
        or tooling.get("execution_performed") is not False
    ):
        raise ProductionControllerError(
            "render_authorization_tooling_invalid",
            "only the bounded Satori/resvg adapter is authorized",
        )
    _validate_subject_crop_guard(tooling)
    return token


def _validated_adapter_record(
    state: Mapping[str, Any],
    request: Mapping[str, Any],
    result: Mapping[str, Any],
) -> Dict[str, Any]:
    candidate_id = _text(request.get("candidate_id"))
    receipt = result.get("receipt") if isinstance(result.get("receipt"), Mapping) else {}
    outputs = [Path(value) for value in result.get("outputs", []) if _text(value)]
    slides = request.get("slides") if isinstance(request.get("slides"), list) else []
    output_hashes = receipt.get("output_hashes") if isinstance(receipt.get("output_hashes"), Mapping) else {}
    if (
        result.get("passed") is not True
        or result.get("status") != "passed"
        or _text(result.get("authorization_id")) != _text(request.get("output_set_id"))
        or _text(receipt.get("candidate_id")) != candidate_id
        or len(outputs) != len(slides)
        or len(outputs) != int(receipt.get("rendered_slide_count") or 0)
    ):
        raise ProductionControllerError("renderer_adapter_receipt_invalid", candidate_id or "missing candidate")
    for slide, output in zip(slides, outputs):
        page = slide.get("page") if isinstance(slide, Mapping) else None
        expected_hash = _text(output_hashes.get(str(page)))
        if not output.is_file() or not expected_hash or _sha256(output) != expected_hash:
            raise ProductionControllerError(
                "renderer_adapter_output_invalid",
                f"{candidate_id} output is missing or differs from its renderer receipt: {output}",
            )
    account_by_candidate = {
        _text(row.get("candidate_id")): _text(row.get("account")).upper()
        for row in state.get("packages", [])
        if isinstance(row, Mapping)
    }
    package_path = Path(_text(request.get("package_path")))
    if not package_path.is_file():
        raise ProductionControllerError(
            "renderer_adapter_package_missing",
            f"{candidate_id} request needs its existing package_path",
        )
    package = _read_json(package_path)
    if not isinstance(package, Mapping):
        raise ProductionControllerError("renderer_adapter_package_invalid", f"{candidate_id} package is not an object")
    _validate_comment_slide_contract(
        candidate_id,
        [dict(slide) if isinstance(slide, Mapping) else {} for slide in slides],
        package,
    )
    return {
        "candidate_id": candidate_id,
        "account": account_by_candidate.get(candidate_id, ""),
        "status": "render_completed_pending_visual_qa",
        "outputs": [str(path) for path in outputs],
        "package_path": str(package_path),
        "real_comment_count": int(request.get("real_comment_count") or 0),
        "renderer_receipt": dict(receipt),
    }


def _expected_slides(manifest: Mapping[str, Any]) -> List[Dict[str, Any]]:
    expected: List[Dict[str, Any]] = []
    for record in manifest.get("records", []):
        if not isinstance(record, Mapping):
            continue
        candidate_id = _text(record.get("candidate_id"))
        account = _text(record.get("account")).upper()
        comment_pages: set[int] = set()
        package_path = Path(_text(record.get("package_path")))
        if not package_path.is_file():
            raise ProductionControllerError(
                "visual_qa_package_missing", f"{candidate_id} package_path is required for visual QA"
            )
        package = _read_json(package_path)
        slides = package.get("slides") if isinstance(package, Mapping) else None
        if not isinstance(slides, list) or not slides:
            raise ProductionControllerError(
                "visual_qa_package_slides_missing", f"{candidate_id} package has no slide contract"
            )
        _validate_comment_slide_contract(
            candidate_id,
            [dict(slide) if isinstance(slide, Mapping) else {} for slide in slides],
            package,
        )
        for index, slide in enumerate(slides, start=1):
            if not isinstance(slide, Mapping):
                raise ProductionControllerError(
                    "visual_qa_package_slide_invalid", f"{candidate_id} slide {index} is invalid"
                )
            if _is_comment_slide(slide):
                comment_pages.add(index)
        try:
            real_comment_count = int(record.get("real_comment_count", 0))
        except (TypeError, ValueError):
            real_comment_count = 0
        if real_comment_count > 0 and not comment_pages:
            raise ProductionControllerError(
                "visual_qa_comment_crop_missing",
                f"{candidate_id} reports comment evidence but has no identifiable readable comment crop",
            )
        output_count = len([value for value in record.get("outputs", []) if _text(value)])
        if any(page > output_count for page in comment_pages):
            raise ProductionControllerError(
                "visual_qa_comment_output_missing",
                f"{candidate_id} comment slide is missing from rendered outputs",
            )
        template_crop_windows = record.get("template_crop_windows")
        if isinstance(template_crop_windows, list):
            template_crop_windows = [item for item in template_crop_windows if isinstance(item, Mapping)]
        for page, raw_path in enumerate(record.get("outputs", []), start=1):
            path = Path(_text(raw_path))
            if not path.is_file():
                raise ProductionControllerError("render_output_missing", str(path))
            template_crop_window = _coerce_template_crop_window(record.get("template_crop_window"))
            if isinstance(template_crop_windows, list) and page - 1 < len(template_crop_windows):
                template_crop_window = _coerce_template_crop_window(template_crop_windows[page - 1]) or template_crop_window

            row: Dict[str, Any] = {
                "account": account,
                "candidate_id": candidate_id,
                "page": page,
                "image_path": str(path),
                "image_sha256": _sha256(path),
                "requires_comment_readability": page in comment_pages,
            }
            if template_crop_window:
                row["template_crop_window"] = template_crop_window
            expected.append(row)
    if not expected:
        raise ProductionControllerError("render_outputs_missing", "manifest contains no rendered slide files")
    return expected


def command_init(args: argparse.Namespace) -> Dict[str, Any]:
    packages = _load_packages(args.packages)
    receipts = [assess_package_completion(package) for package in packages]
    state = initialize_controller(args.controller_id, packages, receipts)
    _atomic_write(args.state, state)
    return state


def command_bind_rules(args: argparse.Namespace) -> Dict[str, Any]:
    return _apply(args.state, BIND_HARD_RULES, args.receipt_id, {"hard_rules": _hard_rules(args.directives)})


def command_transition(args: argparse.Namespace) -> Dict[str, Any]:
    payload = _read_json(args.payload)
    if not isinstance(payload, Mapping):
        raise ProductionControllerError("transition_payload_invalid", "payload file must contain an object")
    return _apply(args.state, args.transition, args.receipt_id, payload)


def command_issue_render(args: argparse.Namespace) -> Dict[str, Any]:
    state = _load_state(args.state)
    output_drive = args.output_root.resolve().drive.upper()
    if os.name == "nt" and output_drive != "F:" and not getattr(args, "allow_non_f_test_output", False):
        raise ProductionControllerError(
            "heavy_output_must_use_f_drive",
            "CardNews render output must use the configured F: data location",
        )
    mode = args.mode
    expected_state = REPRESENTATIVE_AUTHORIZED if mode == "representative" else BATCH_AUTHORIZED
    if state.get("state") != expected_state:
        raise ProductionControllerError("render_not_authorized", f"controller state must be {expected_state}")
    candidate_ids = (
        sorted(state.get("representatives", {}).values())
        if mode == "representative"
        else sorted(state.get("candidate_ids", []))
    )
    media_hashes = state.get("local_media_receipt_hashes")
    media_sources = state.get("local_media_source_bindings")
    if not isinstance(media_hashes, Mapping) or any(
        not isinstance(media_hashes.get(candidate_id), list) or not media_hashes.get(candidate_id)
        for candidate_id in candidate_ids
    ):
        raise ProductionControllerError(
            "local_media_authorization_missing",
            "every authorized candidate needs completed local-media preparation receipts",
        )
    if not isinstance(media_sources, Mapping):
        raise ProductionControllerError(
            "local_media_source_binding_missing", "prepared source bindings are required"
        )
    for candidate_id in candidate_ids:
        bindings = media_sources.get(candidate_id)
        if not isinstance(bindings, list) or not bindings:
            raise ProductionControllerError(
                "local_media_source_binding_missing", f"{candidate_id} has no prepared source binding"
            )
        for binding in bindings:
            path = Path(_text(binding.get("source_path"))) if isinstance(binding, Mapping) else Path()
            expected_hash = _text(binding.get("source_sha256")) if isinstance(binding, Mapping) else ""
            if not path.is_file() or not expected_hash or _sha256(path) != expected_hash:
                raise ProductionControllerError(
                    "local_media_source_stale",
                    f"{candidate_id} prepared source is missing or changed: {path}",
                )
    representative_qa_ids = state.get("representative_qa_receipt_ids", {})
    if mode == "batch" and (
        not isinstance(representative_qa_ids, Mapping)
        or set(representative_qa_ids) != set(state.get("accounts", []))
        or any(not _text(value) for value in representative_qa_ids.values())
    ):
        raise ProductionControllerError(
            "representative_visual_qa_missing",
            "batch tooling and renderer entry require one independent visual-QA receipt per account",
        )
    expiry = datetime.now().astimezone() + timedelta(minutes=args.ttl_minutes)
    token_body = {
        "schema_version": "cardnews_render_authorization_v1",
        "authorized": True,
        "mode": mode,
        "candidate_ids": candidate_ids,
        "input_sha256": _fragment_digest(args.input_root),
        "output_root": str(args.output_root.resolve()),
        "expires_at": expiry.isoformat(),
        "controller_state_path": str(args.state.resolve()),
        "controller_state_hash": state["state_hash"],
        "controller_id": state["controller_id"],
        "hard_rule_hash": state["hard_rule_hash"],
        "batch_hash": state["batch_hash"],
        "local_media_receipt_hashes": {
            candidate_id: list(media_hashes[candidate_id]) for candidate_id in candidate_ids
        },
        "local_media_binding_hash": canonical_hash(
            {candidate_id: list(media_hashes[candidate_id]) for candidate_id in candidate_ids}
        ),
        "representative_visual_qa_receipt_ids": dict(representative_qa_ids) if mode == "batch" else {},
        "tooling_authorization": {
            "satori": True,
            "resvg": True,
            "fabric": False,
            "motion": False,
            "renderer": True,
            "scope": mode,
            "representative_qa_gate_satisfied": mode == "batch",
            "authorization_metadata_only": True,
            "execution_performed": False,
            "subject_crop_guard": {
                "enabled": True,
                "policy_version": SUBJECT_CROP_GUARD_POLICY_VERSION,
                "version": SUBJECT_CROP_GUARD_POLICY_VERSION,
                "scope": SUBJECT_CROP_GUARD_SCOPE,
                "mode": SUBJECT_CROP_GUARD_POLICY_MODE,
                "frame_profile": SUBJECT_CROP_GUARD_FRAME_PROFILE,
                "bbox_source": SUBJECT_CROP_GUARD_BBOX_SOURCE,
                "reason_prefix": SUBJECT_CROP_GUARD_REASON_PREFIX,
                "max_subject_outside_ratio": SUBJECT_CROP_GUARD_MAX_SUBJECT_OUTSIDE_RATIO,
                "min_subject_kept_ratio": SUBJECT_CROP_GUARD_MIN_SUBJECT_KEPT_RATIO,
                "metric_precision": SUBJECT_CROP_GUARD_METRIC_PRECISION,
            },
        },
    }
    token_body["authorization_id"] = f"render-{canonical_hash(token_body)[:24]}"
    _atomic_write(args.authorization, token_body)
    return token_body


def command_execute_render_adapter(args: argparse.Namespace) -> Dict[str, Any]:
    if (
        isinstance(args.timeout_seconds, bool)
        or args.timeout_seconds <= 0
        or args.timeout_seconds > MAX_RENDER_TIMEOUT_SECONDS
    ):
        raise ProductionControllerError(
            "renderer_adapter_timeout_invalid",
            f"timeout_seconds must be > 0 and <= {MAX_RENDER_TIMEOUT_SECONDS:g}",
        )
    state = _load_state(args.state)
    authorization = _read_json(args.authorization)
    requests = _adapter_requests(_read_json(args.render_request))
    token = _validate_adapter_authorization(authorization, state, requests)
    consumption_path = _adapter_consumption_path(token)
    if consumption_path.exists():
        raise ProductionControllerError(
            "render_authorization_reused",
            f"authorization already claimed: {token['authorization_id']}",
        )

    runtime = getattr(args, "renderer_runtime", None) or CardNewsRendererRuntime(
        getattr(args, "renderer_tool_root", None),
        node_executable=getattr(args, "node_executable", None),
    )
    for request in requests:
        contract = runtime.render_contract(
            state,
            request,
            authorization=token,
            timeout_seconds=args.timeout_seconds,
        )
        if not isinstance(contract, Mapping) or contract.get("ready") is not True or contract.get("subprocess_allowed") is not True:
            raise ProductionControllerError(
                "renderer_adapter_blocked",
                _text(contract.get("reason")) if isinstance(contract, Mapping) else "invalid render contract",
            )

    claim = {
        "schema_version": "cardnews_render_authorization_consumption_v2",
        "status": "claimed",
        "authorization_id": token["authorization_id"],
        "controller_state_hash": state["state_hash"],
        "candidate_ids": sorted(token["candidate_ids"]),
        "claimed_at": datetime.now().astimezone().isoformat(),
        "renderer_entry": "cardnews_renderer_runtime",
    }
    _atomic_create(consumption_path, claim)

    results: List[Dict[str, Any]] = []
    try:
        for request in requests:
            result = runtime.run_render(
                state,
                request,
                authorization=token,
                timeout_seconds=args.timeout_seconds,
            )
            if not isinstance(result, Mapping) or result.get("passed") is not True:
                reason = _text(result.get("reason")) if isinstance(result, Mapping) else "invalid renderer result"
                raise ProductionControllerError("renderer_adapter_execution_failed", reason)
            results.append(dict(result))
        records = [
            _validated_adapter_record(state, request, result)
            for request, result in zip(requests, results)
        ]
        manifest: Dict[str, Any] = {
            "schema_version": "cardnews_render_review_manifest_v2",
            "renderer_entry": "cardnews_renderer_runtime",
            "authorization_id": token["authorization_id"],
            "output_set_id": token["authorization_id"],
            "controller_state_hash": state["state_hash"],
            "batch_hash": state["batch_hash"],
            "hard_rule_hash": state["hard_rule_hash"],
            "render_mode": token["mode"],
            "local_media_binding_hash": token["local_media_binding_hash"],
            "records": records,
        }
        manifest["adapter_execution_hash"] = canonical_hash(manifest)
        _atomic_write(args.manifest, manifest)
        completed = {
            **claim,
            "status": "completed",
            "completed_at": datetime.now().astimezone().isoformat(),
            "manifest_path": str(args.manifest.resolve()),
            "manifest_sha256": _sha256(args.manifest),
            "adapter_execution_hash": manifest["adapter_execution_hash"],
        }
        _atomic_write(consumption_path, completed)
        return manifest
    except Exception as exc:
        failed = {
            **claim,
            "status": "failed",
            "failed_at": datetime.now().astimezone().isoformat(),
            "reason": f"{type(exc).__name__}:{exc}",
        }
        _atomic_write(consumption_path, failed)
        raise


def command_record_render(args: argparse.Namespace) -> Dict[str, Any]:
    manifest = _read_json(args.manifest)
    state = _load_state(args.state)
    authorization = _read_json(args.authorization)
    token = _validate_render_authorization(authorization, manifest, state)
    if _text(manifest.get("renderer_entry")) == "cardnews_renderer_runtime":
        consumption_path = _adapter_consumption_path(token)
        try:
            consumption = _read_json(consumption_path)
        except (OSError, json.JSONDecodeError) as exc:
            raise ProductionControllerError(
                "renderer_adapter_consumption_missing", str(consumption_path)
            ) from exc
        if (
            not isinstance(consumption, Mapping)
            or consumption.get("status") != "completed"
            or _text(consumption.get("authorization_id")) != token["authorization_id"]
            or _text(consumption.get("controller_state_hash")) != state["state_hash"]
            or _text(consumption.get("manifest_path")) != str(args.manifest.resolve())
            or _text(consumption.get("manifest_sha256")) != _sha256(args.manifest)
            or _text(consumption.get("adapter_execution_hash")) != _text(manifest.get("adapter_execution_hash"))
        ):
            raise ProductionControllerError(
                "renderer_adapter_consumption_invalid",
                "adapter manifest is not bound to its completed one-time authorization claim",
            )
    manifest = dict(manifest)
    manifest["local_media_binding_hash"] = token["local_media_binding_hash"]
    receipts = _render_receipts(manifest)
    transition = (
        RECORD_REPRESENTATIVE_RENDER
        if state.get("state") == REPRESENTATIVE_AUTHORIZED
        else RECORD_BATCH_RENDER
    )
    return _apply(
        args.state,
        transition,
        args.receipt_id,
        {"render_receipts": receipts},
    )


def command_accept_visual_qa(args: argparse.Namespace) -> Dict[str, Any]:
    manifest = _read_json(args.manifest)
    expected = _expected_slides(manifest)
    state = _load_state(args.state)
    transition = (
        ACCEPT_REPRESENTATIVE_QA
        if state.get("state") == "representative_render_recorded"
        else ACCEPT_BATCH_QA
    )
    required_candidates = (
        set(state.get("representatives", {}).values())
        if transition == ACCEPT_REPRESENTATIVE_QA
        else set(state.get("candidate_ids", []))
    )
    raw_receipts = _read_json(args.qa_receipt)
    if isinstance(raw_receipts, Mapping) and isinstance(raw_receipts.get("receipts"), list):
        receipt_rows = raw_receipts["receipts"]
    elif isinstance(raw_receipts, list):
        receipt_rows = raw_receipts
    else:
        receipt_rows = [raw_receipts]
    qa_results: Dict[str, Dict[str, Any]] = {}
    for raw in receipt_rows:
        if not isinstance(raw, Mapping):
            raise ProductionControllerError("visual_qa_receipt_invalid", "each QA receipt must be an object")
        scope = raw.get("scope") if isinstance(raw.get("scope"), Mapping) else {}
        scoped_candidates = {
            _text(value) for value in scope.get("candidate_ids", []) if _text(value)
        }
        scoped_expected = [row for row in expected if row["candidate_id"] in scoped_candidates]
        result = assess_visual_qa_receipt(
            raw,
            scoped_expected,
            expected_output_set_id=_text(manifest.get("output_set_id")),
            expected_representative_receipt_ids=(
                state.get("representative_qa_receipt_ids")
                if transition == ACCEPT_BATCH_QA
                else None
            ),
        )
        if not result.get("visual_qa_passed"):
            raise ProductionControllerError(
                "visual_qa_failed", json.dumps(result.get("failures", []), ensure_ascii=False)
            )
        for candidate_id in scoped_candidates:
            if candidate_id in qa_results:
                raise ProductionControllerError("visual_qa_duplicate_candidate", candidate_id)
            qa_results[candidate_id] = {**result, "candidate_id": candidate_id}
    if set(qa_results) != required_candidates:
        raise ProductionControllerError(
            "visual_qa_scope_incomplete",
            f"expected {sorted(required_candidates)}, received {sorted(qa_results)}",
        )
    return _apply(
        args.state,
        transition,
        args.receipt_id,
        {
            "visual_qa_receipts": qa_results,
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("--packages", type=Path, required=True)
    init.add_argument("--state", type=Path, required=True)
    init.add_argument("--controller-id", required=True)
    init.set_defaults(handler=command_init)

    rules = sub.add_parser("bind-hard-rules")
    rules.add_argument("--state", type=Path, required=True)
    rules.add_argument("--receipt-id", required=True)
    rules.add_argument("--directives", type=Path, default=DEFAULT_DIRECTIVES)
    rules.set_defaults(handler=command_bind_rules)

    transition = sub.add_parser("transition")
    transition.add_argument("--state", type=Path, required=True)
    transition.add_argument("--transition", required=True, choices=(AUTHORIZE_REPRESENTATIVES, AUTHORIZE_BATCH))
    transition.add_argument("--receipt-id", required=True)
    transition.add_argument("--payload", type=Path, required=True)
    transition.set_defaults(handler=command_transition)

    token = sub.add_parser("issue-render-authorization")
    token.add_argument("--state", type=Path, required=True)
    token.add_argument("--mode", choices=("representative", "batch"), required=True)
    token.add_argument("--input-root", type=Path, required=True)
    token.add_argument("--output-root", type=Path, required=True)
    token.add_argument("--authorization", type=Path, required=True)
    token.add_argument("--ttl-minutes", type=int, default=10, choices=range(1, 31))
    token.set_defaults(handler=command_issue_render)

    adapter = sub.add_parser("execute-render-adapter")
    adapter.add_argument("--state", type=Path, required=True)
    adapter.add_argument("--authorization", type=Path, required=True)
    adapter.add_argument("--render-request", type=Path, required=True)
    adapter.add_argument("--manifest", type=Path, required=True)
    adapter.add_argument("--renderer-tool-root", type=Path)
    adapter.add_argument("--node-executable", type=Path)
    adapter.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_RENDER_TIMEOUT_SECONDS,
    )
    adapter.set_defaults(handler=command_execute_render_adapter)

    rendered = sub.add_parser("record-render")
    rendered.add_argument("--state", type=Path, required=True)
    rendered.add_argument("--manifest", type=Path, required=True)
    rendered.add_argument("--authorization", type=Path, required=True)
    rendered.add_argument("--receipt-id", required=True)
    rendered.set_defaults(handler=command_record_render)

    qa = sub.add_parser("accept-visual-qa")
    qa.add_argument("--state", type=Path, required=True)
    qa.add_argument("--manifest", type=Path, required=True)
    qa.add_argument("--qa-receipt", type=Path, required=True)
    qa.add_argument("--receipt-id", required=True)
    qa.set_defaults(handler=command_accept_visual_qa)

    status = sub.add_parser("status")
    status.add_argument("--state", type=Path, required=True)
    status.set_defaults(handler=lambda args: _load_state(args.state))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = args.handler(args)
    except (OSError, json.JSONDecodeError, ProductionControllerError, PermissionError) as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({
        "status": result.get("state") or result.get("status") or "ok",
        "controller_id": result.get("controller_id"),
        "state_hash": result.get("state_hash"),
        "manual_upload_ready": result.get("manual_upload_ready", False),
        "authorization_id": result.get("authorization_id"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
