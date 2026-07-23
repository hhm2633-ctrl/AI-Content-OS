"""Build a story cover from real, identity-masked comment crops."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import hashlib
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Mapping, Sequence

from PIL import Image, ImageDraw, ImageOps

from modules.tool_adapters.paddleocr_runtime import extract_korean_text


CANVAS_SIZE = (1080, 1350)
MAX_OCR_CANDIDATES = 4
SPOTLIGHT_COUNT = 2


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _receipt_mapping(value: Any) -> Dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    return dict(value) if isinstance(value, Mapping) else {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reaction_count(receipt: Mapping[str, Any], image_width: int) -> int:
    lines = receipt.get("lines")
    boxes = receipt.get("boxes")
    if not isinstance(lines, (list, tuple)):
        return -1
    candidates: List[int] = []
    for line in lines:
        value = _text(line).replace(",", "")
        if not re.fullmatch(r"\d{1,6}", value):
            continue
        candidates.append(int(value))
    return max(candidates, default=-1)


def _controversy_score(text: str) -> int:
    normalized = _text(text)
    markers = (
        "ㅋㅋ",
        "둘째",
        "남편",
        "아내",
        "육아",
        "혼자만의 시간",
        "이상",
        "거부",
        "불쌍",
        "왜",
        "?",
        "!",
    )
    return sum(normalized.count(marker) for marker in markers)


def _fit_comment(source: Image.Image, max_width: int, max_height: int) -> Image.Image:
    prepared = ImageOps.exif_transpose(source).convert("RGB")
    ratio = min(max_width / prepared.width, max_height / prepared.height)
    size = (
        max(1, round(prepared.width * ratio)),
        max(1, round(prepared.height * ratio)),
    )
    return prepared.resize(size, Image.Resampling.LANCZOS)


def _compose(selected: Sequence[Mapping[str, Any]], output_path: Path) -> None:
    canvas = Image.new("RGB", CANVAS_SIZE, "#F8EEE8")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 1080, 1350), fill="#F8EEE8")
    draw.rounded_rectangle((44, 205, 1036, 930), radius=42, fill="#241D21")
    draw.rounded_rectangle((70, 225, 1010, 910), radius=30, fill="#FFF9F5")
    draw.rectangle((70, 225, 1010, 239), fill="#F07191")

    y_positions = (275, 600)
    for index, comment in enumerate(selected[:SPOTLIGHT_COUNT]):
        source_path = Path(_text(comment.get("screenshot_path"))).resolve()
        with Image.open(source_path) as source:
            prepared = _fit_comment(source, 900, 275)
        x = (1080 - prepared.width) // 2
        y = y_positions[index]
        shadow = (x + 10, y + 12, x + prepared.width + 10, y + prepared.height + 12)
        draw.rounded_rectangle(shadow, radius=18, fill="#D8C7C3")
        frame = (x - 8, y - 8, x + prepared.width + 8, y + prepared.height + 8)
        draw.rounded_rectangle(frame, radius=18, fill="#FFFFFF", outline="#F07191", width=4)
        canvas.paste(prepared, (x, y))

    # The approved cover blueprint overlaps its white headline with the lower
    # edge of the media region. Preserve contrast inside the source image.
    draw.rectangle((0, 980, 1080, 1350), fill="#171717")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="PNG", optimize=True)


def build_story_comment_spotlight(
    comments: Sequence[Mapping[str, Any]],
    output_path: str | Path,
    *,
    ocr_extractor: Callable[..., Any] = extract_korean_text,
    ocr_timeout_seconds: float = 30.0,
) -> Dict[str, Any]:
    """Rank eligible real comments and compose two readable cover crops."""

    eligible: List[Dict[str, Any]] = []
    for position, raw in enumerate(comments, start=1):
        if not isinstance(raw, Mapping):
            continue
        screenshot = Path(_text(raw.get("screenshot_path"))).expanduser()
        if (
            raw.get("is_real_comment") is not True
            or raw.get("identity_masked") is not True
            or raw.get("comment_slide_eligible") is not True
            or not screenshot.is_absolute()
            or not screenshot.is_file()
        ):
            continue
        with Image.open(screenshot) as image:
            width = image.width
        receipt: Dict[str, Any] = {}
        if len(eligible) < MAX_OCR_CANDIDATES:
            try:
                receipt = _receipt_mapping(
                    ocr_extractor(
                        str(screenshot),
                        timeout_seconds=ocr_timeout_seconds,
                    )
                )
            except Exception as error:
                receipt = {
                    "success": False,
                    "status": "failed",
                    "reason": type(error).__name__,
                }
        reaction_count = (
            _reaction_count(receipt, width)
            if receipt.get("success") is True
            else -1
        )
        eligible.append(
            {
                "comment_id": _text(raw.get("comment_id")) or f"comment-{position}",
                "text": _text(raw.get("text")),
                "source_url": _text(raw.get("source_url")),
                "screenshot_path": str(screenshot.resolve()),
                "screenshot_sha256": _sha256(screenshot.resolve()),
                "identity_masked": True,
                "comment_slide_eligible": True,
                "source_order": position,
                "reaction_count": reaction_count,
                "controversy_score": _controversy_score(_text(raw.get("text"))),
                "ocr_status": _text(receipt.get("status")) or "not_run",
                "ocr_reason": _text(receipt.get("reason")),
            }
        )

    if not eligible:
        return {
            "status": "blocked",
            "reason_code": "eligible_masked_comment_crop_missing",
            "selected": [],
            "spotlight_selected": [],
        }

    ranked = sorted(
        eligible,
        key=lambda item: (
            item["reaction_count"],
            item["controversy_score"],
            -item["source_order"],
        ),
        reverse=True,
    )
    spotlight = ranked[: min(SPOTLIGHT_COUNT, len(ranked))]
    target = Path(output_path).expanduser().resolve()
    _compose(spotlight, target)
    source_url = _text(spotlight[0].get("source_url"))
    media_asset = {
        "asset_id": "story-comment-spotlight-cover",
        "path": str(target),
        "local_path": str(target),
        "source_url": source_url,
        "rights_status": "source_attributed_review_only",
        "publish_authorized": False,
        "crop_allowed": True,
        "aspect_ratio": round(CANVAS_SIZE[0] / CANVAS_SIZE[1], 6),
    }
    return {
        "status": "ready",
        "reason_code": "masked_comment_spotlight_composed",
        "selected": eligible,
        "spotlight_selected": spotlight,
        "media_asset": media_asset,
        "output_path": str(target),
        "output_sha256": _sha256(target),
        "source_modified": False,
        "publish_authorized": False,
    }


__all__ = ["build_story_comment_spotlight"]
