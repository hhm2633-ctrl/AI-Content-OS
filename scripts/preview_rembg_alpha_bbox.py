from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from modules.media_intelligence.rembg_bbox import extract_subject_bbox_from_alpha
from modules.tool_adapters.rembg_runtime import RembgRuntimeAdapter


ROOT = Path("C:/Users/가산 솔리드옴므/Documents/GitHub/AI-Content-OS")

INPUT_IMAGES = [
    ROOT / "storage/cache/qa_threshold_sample/dior_runway_01.png",
    ROOT / "storage/cache/qa_threshold_sample/dior_runway_13.png",
    ROOT / "storage/cache/qa_threshold_sample/dior_runway_18.png",
]

OUTPUT_ROOT = ROOT / "artifacts/rembg_alpha_bbox_stage1"
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def _draw_bbox(image_path: Path, bbox: dict[str, int], out_path: Path) -> None:
    with Image.open(image_path) as image:
        canvas = image.convert("RGB")
    draw = ImageDraw.Draw(canvas)
    x = bbox["x"]
    y = bbox["y"]
    w = bbox["width"]
    h = bbox["height"]
    draw.rectangle((x, y, x + w - 1, y + h - 1), outline=(255, 0, 0), width=4)
    canvas.save(out_path)


def main() -> None:
    rembg = RembgRuntimeAdapter()
    summary = {
        "inputs": [],
        "rembg_status": rembg.readiness(),
    }

    for source in INPUT_IMAGES:
        cutout_path = OUTPUT_ROOT / f"{source.stem}_rembg.png"
        overlay_path = OUTPUT_ROOT / f"{source.stem}_bbox_overlay.png"

        remove_result = rembg.cutout(source, cutout_path)
        if remove_result.get("status") != "completed":
            summary["inputs"].append(
                {
                    "source": str(source),
                    "status": "rembg_failed",
                    "remove_result": remove_result,
                }
            )
            continue

        bbox_result = extract_subject_bbox_from_alpha(
            cutout_path,
            alpha_threshold=8,
            min_area=200,
            margin_ratio=0.01,
            component="largest",
        )

        if bbox_result.get("status") == "ok":
            _draw_bbox(source, bbox_result["primary_bbox"], overlay_path)

        summary["inputs"].append(
            {
                "source": str(source),
                "status": bbox_result.get("status"),
                "rembg": {"output": str(cutout_path), "status": remove_result.get("status")},
                "bbox": bbox_result,
                "overlay": str(overlay_path),
            }
        )

    summary_path = OUTPUT_ROOT / "bbox_preview_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE {summary_path}")


if __name__ == "__main__":
    main()
