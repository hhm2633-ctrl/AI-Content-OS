"""Deterministic Pillow contact sheets for local design-learning assets."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

from PIL import Image, ImageDraw, ImageFont, ImageOps


def generate_contact_sheet(
    entries: Iterable[Dict[str, Any]],
    output_root: Path,
    output_path: Path,
    *,
    columns: int = 4,
) -> Dict[str, Any]:
    """Render staged unique images in stable source-path order.

    Rendering failure is data, not an exception: callers always receive a
    status dictionary suitable for embedding in the intake manifest.
    """
    warnings: List[str] = []
    usable = sorted(
        (
            entry
            for entry in entries
            if entry.get("status") == "unique" and entry.get("staged_relative_path")
        ),
        key=lambda entry: str(entry.get("source_relative_path", "")).casefold(),
    )
    if not usable:
        return {
            "status": "skipped",
            "image_count": 0,
            "columns": columns,
            "rows": 0,
            "included_asset_ids": [],
            "warnings": ["no_staged_unique_images"],
        }

    columns = max(1, int(columns))
    thumb_width, thumb_height = 240, 180
    label_height, padding = 42, 12
    cell_width = thumb_width + padding * 2
    cell_height = thumb_height + label_height + padding * 2
    rows = (len(usable) + columns - 1) // columns
    sheet = Image.new("RGB", (cell_width * columns, cell_height * rows), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    included: List[str] = []

    try:
        for index, entry in enumerate(usable):
            staged_path = output_root / str(entry["staged_relative_path"])
            with Image.open(staged_path) as opened:
                image = ImageOps.exif_transpose(opened).convert("RGB")
                image.thumbnail((thumb_width, thumb_height), Image.Resampling.LANCZOS)

            row, column = divmod(index, columns)
            x0 = column * cell_width + padding
            y0 = row * cell_height + padding
            x = x0 + (thumb_width - image.width) // 2
            y = y0 + (thumb_height - image.height) // 2
            sheet.paste(image, (x, y))
            draw.rectangle(
                (x0, y0, x0 + thumb_width, y0 + thumb_height),
                outline=(210, 210, 210),
                width=1,
            )
            label = f"{index + 1}. {entry.get('source_relative_path', '')}"
            draw.text(
                (x0, y0 + thumb_height + 8),
                label[:52],
                fill=(35, 35, 35),
                font=font,
            )
            included.append(str(entry.get("asset_id")))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
        sheet.save(temporary_path, format="PNG", optimize=False)
        temporary_path.replace(output_path)
        return {
            "status": "created",
            "image_count": len(included),
            "columns": columns,
            "rows": rows,
            "included_asset_ids": included,
            "warnings": warnings,
        }
    except Exception as error:
        return {
            "status": "failed",
            "image_count": len(included),
            "columns": columns,
            "rows": rows,
            "included_asset_ids": included,
            "warnings": [f"contact_sheet_error:{type(error).__name__}"],
        }
    finally:
        sheet.close()

