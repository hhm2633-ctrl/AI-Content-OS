"""Render traced local source images into one short 4:5 MP4 montage.

This is a local editing utility, not a generative-video provider.  It performs
no search, download, publishing, or WorkflowEngine integration.
"""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import imageio_ffmpeg
from PIL import Image


SCHEMA_VERSION = "source_image_motion_montage_v1"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_ORIGINS = {"official", "owned", "licensed", "user_supplied"}
BLOCKED_RIGHTS = {"restricted", "blocked", "third_party_unlicensed_reference"}
RESAMPLE = Image.Resampling.LANCZOS


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _blocked(reason_code: str, reason: str, diagnostics: Any = None) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "blocked",
        "reason_code": reason_code,
        "reason": reason,
        "render_executed": False,
        "publish_executed": False,
        "output_path": None,
        "source_manifest_path": None,
        "diagnostics": diagnostics if isinstance(diagnostics, list) else [],
    }


def _validate_records(records: Any) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not isinstance(records, list):
        return [], [{"reason_code": "records_not_list"}]
    normalized: List[Dict[str, Any]] = []
    diagnostics: List[Dict[str, Any]] = []
    for position, raw in enumerate(records, start=1):
        if not isinstance(raw, Mapping):
            diagnostics.append({"position": position, "reason_code": "record_not_object"})
            continue

        local_path = Path(_text(raw.get("local_path")))
        source_url = _text(raw.get("source_url"))
        origin = _text(raw.get("origin")).lower()
        rights_status = _text(raw.get("rights_status")).lower() or "unrecorded"
        agency = _text(raw.get("agency")).lower()

        reasons: List[str] = []
        if not _text(raw.get("local_path")) or not local_path.is_file():
            reasons.append("local_file_missing")
        elif local_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            reasons.append("unsupported_image_type")
        if not source_url:
            reasons.append("source_url_missing")
        if origin not in ALLOWED_ORIGINS:
            reasons.append("origin_not_allowed")
        if origin == "generated":
            reasons.append("generated_product_image_blocked")
        if raw.get("reference_only") is True:
            reasons.append("reference_only")
        if raw.get("ap_source") is True or agency in {"ap", "associated press"}:
            reasons.append("ap_reference_only")
        if rights_status in BLOCKED_RIGHTS:
            reasons.append("rights_blocked")

        if reasons:
            diagnostics.append(
                {"position": position, "local_path": str(local_path), "reason_codes": reasons}
            )
            continue

        try:
            with Image.open(local_path) as image:
                image.verify()
        except (OSError, ValueError):
            diagnostics.append(
                {
                    "position": position,
                    "local_path": str(local_path),
                    "reason_codes": ["image_decode_failed"],
                }
            )
            continue

        normalized.append(
            {
                "sequence": position,
                "local_path": str(local_path.resolve()),
                "source_url": source_url,
                "origin": origin,
                "rights_status": rights_status,
                "source_name": _text(raw.get("source_name")),
                "asset_id": _text(raw.get("asset_id")) or f"asset-{position}",
            }
        )
    return normalized, diagnostics


def _ease(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def _cover_frame(
    image: Image.Image,
    progress: float,
    width: int,
    height: int,
    direction: int,
) -> Image.Image:
    progress = _ease(progress)
    zoom = 1.015 + 0.09 * progress
    scale = max(width / image.width, height / image.height) * zoom
    resized = image.resize(
        (max(width, math.ceil(image.width * scale)), max(height, math.ceil(image.height * scale))),
        RESAMPLE,
    )
    excess_x = resized.width - width
    excess_y = resized.height - height
    horizontal = 0.5 + direction * (progress - 0.5) * 0.32
    vertical = 0.5 - direction * (progress - 0.5) * 0.12
    left = round(max(0, min(excess_x, excess_x * horizontal)))
    top = round(max(0, min(excess_y, excess_y * vertical)))
    return resized.crop((left, top, left + width, top + height)).convert("RGB")


def _open_images(records: Sequence[Mapping[str, Any]]) -> List[Image.Image]:
    images: List[Image.Image] = []
    for record in records:
        with Image.open(record["local_path"]) as image:
            images.append(image.convert("RGB"))
    return images


def _frame_at(
    images: Sequence[Image.Image],
    time_value: float,
    seconds_per_image: float,
    transition_seconds: float,
    width: int,
    height: int,
) -> Image.Image:
    index = min(len(images) - 1, int(time_value / seconds_per_image))
    local_time = time_value - index * seconds_per_image
    progress = min(1.0, local_time / seconds_per_image)
    current = _cover_frame(images[index], progress, width, height, 1 if index % 2 == 0 else -1)
    fade_start = seconds_per_image - transition_seconds
    if index < len(images) - 1 and transition_seconds > 0 and local_time >= fade_start:
        blend = _ease((local_time - fade_start) / transition_seconds)
        following = _cover_frame(images[index + 1], 0.0, width, height, -1 if index % 2 == 0 else 1)
        return Image.blend(current, following, blend)
    return current


def _encode(
    images: Sequence[Image.Image],
    output_path: Path,
    *,
    width: int,
    height: int,
    fps: int,
    seconds_per_image: float,
    transition_seconds: float,
) -> int:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{width}x{height}",
        "-r",
        str(fps),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    if process.stdin is None:
        process.kill()
        raise RuntimeError("ffmpeg stdin unavailable")
    total_frames = max(1, round(len(images) * seconds_per_image * fps))
    try:
        for frame_index in range(total_frames):
            time_value = frame_index / fps
            frame = _frame_at(
                images,
                time_value,
                seconds_per_image,
                transition_seconds,
                width,
                height,
            )
            process.stdin.write(frame.tobytes())
    finally:
        process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError("ffmpeg encode failed")
    return total_frames


def render_source_image_motion_montage(
    image_records: Any,
    output_path: Any,
    *,
    width: int = 1080,
    height: int = 1350,
    fps: int = 24,
    seconds_per_image: float = 1.0,
    transition_seconds: float = 0.22,
) -> Dict[str, Any]:
    """Render an MP4 and adjacent source manifest from traced local images."""

    records, diagnostics = _validate_records(image_records)
    if len(records) < 2:
        return _blocked(
            "insufficient_valid_images",
            "at least two valid traced local images are required",
            diagnostics,
        )
    if len(records) > 12:
        return _blocked("too_many_images", "a montage accepts at most twelve images", diagnostics)
    if not isinstance(width, int) or not isinstance(height, int) or width < 64 or height < 64:
        return _blocked("invalid_dimensions", "width and height must be integers >= 64", diagnostics)
    if not isinstance(fps, int) or fps < 1 or fps > 60:
        return _blocked("invalid_fps", "fps must be between 1 and 60", diagnostics)
    if seconds_per_image <= 0:
        return _blocked("invalid_duration", "seconds_per_image must be positive", diagnostics)
    if transition_seconds < 0 or transition_seconds >= seconds_per_image:
        return _blocked(
            "invalid_transition",
            "transition_seconds must be nonnegative and shorter than seconds_per_image",
            diagnostics,
        )

    output = Path(output_path)
    if output.suffix.lower() != ".mp4":
        return _blocked("output_type_invalid", "output path must end in .mp4", diagnostics)

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        images = _open_images(records)
        frame_count = _encode(
            images,
            output,
            width=width,
            height=height,
            fps=fps,
            seconds_per_image=seconds_per_image,
            transition_seconds=transition_seconds,
        )
        manifest_path = output.with_suffix(".source.json")
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "output_file": output.name,
            "method": "source_still_images_zoom_pan_crossfade",
            "generated_source_footage": False,
            "width": width,
            "height": height,
            "fps": fps,
            "duration_seconds": round(frame_count / fps, 3),
            "frame_count": frame_count,
            "sources": records,
        }
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception as error:  # fallback-first utility contract
        output.unlink(missing_ok=True)
        return _blocked(
            "render_failed",
            f"motion montage rendering failed ({type(error).__name__})",
            diagnostics,
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "motion_montage_ready",
        "reason_code": "local_source_images_rendered",
        "render_executed": True,
        "publish_executed": False,
        "output_path": str(output),
        "source_manifest_path": str(manifest_path),
        "image_count": len(records),
        "frame_count": frame_count,
        "duration_seconds": round(frame_count / fps, 3),
        "diagnostics": diagnostics,
    }


__all__ = ["render_source_image_motion_montage", "SCHEMA_VERSION"]
