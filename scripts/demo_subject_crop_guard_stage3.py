"""Generate a quick Stage-3 crop-guard validation sample on QA threshold images."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.media_intelligence.rembg_bbox import extract_subject_bbox_from_alpha
from modules.card_news.canvas_contract import DEFAULT_CARD_CANVAS_SIZE
from scripts.run_cardnews_production import (
    SUBJECT_CROP_GUARD_MAX_SUBJECT_OUTSIDE_RATIO,
    SUBJECT_CROP_GUARD_METRIC_PRECISION,
    _evaluate_subject_crop_guard,
)

INPUT_IMAGES = [
    ROOT / "storage/cache/qa_threshold_sample/dior_runway_01.png",
    ROOT / "storage/cache/qa_threshold_sample/dior_runway_13.png",
    ROOT / "storage/cache/qa_threshold_sample/dior_runway_18.png",
]
REMBG_ROOT = ROOT / "artifacts/rembg_alpha_bbox_stage1"
OUT_ROOT = ROOT / "artifacts/stage3_subject_crop_guard"
OUT_ROOT.mkdir(parents=True, exist_ok=True)

RATIO_TARGETS: List[Tuple[str, float, float]] = [
    ("near_pass", 0.03, 0.04),
    ("near_fail", 0.08, 0.10),
]


def _find_crop_window_for_ratio(
    source_size: tuple[int, int],
    subject_bbox: Dict[str, int],
    min_ratio: float,
    max_ratio: float,
) -> tuple[Dict[str, float], Dict[str, object], bool]:
    width, height = source_size
    best_window: Dict[str, float] | None = None
    best_metric: Dict[str, object] | None = None
    best_gap = float("inf")

    for crop_x in range(0, width + 1):
        window = {
            "x": float(crop_x),
            "y": 0.0,
            "width": float(width),
            "height": float(height),
        }
        metric = _evaluate_subject_crop_guard(
            subject_bbox,
            source_size,
            template_size=DEFAULT_CARD_CANVAS_SIZE,
            template_crop_window=window,
            max_subject_outside_ratio=SUBJECT_CROP_GUARD_MAX_SUBJECT_OUTSIDE_RATIO,
            metric_precision=SUBJECT_CROP_GUARD_METRIC_PRECISION,
        )
        ratio = metric.get("subject_crop_outside_ratio_in_template_frame", 1.0)
        if ratio is not None and min_ratio <= ratio <= max_ratio:
            return window, metric, True

        if ratio is not None:
            gap = min(abs(float(ratio) - min_ratio), abs(float(ratio) - max_ratio))
            if gap < best_gap:
                best_gap = gap
                best_window = window
                best_metric = metric

    if best_window is None:
        best_window = {"x": 0.0, "y": 0.0, "width": float(width), "height": float(height)}
        best_metric = {
            "subject_crop_outside_ratio": 1.0,
            "subject_crop_outside_ratio_in_template_frame": 1.0,
            "subject_crop_pass": False,
        }
    return best_window, best_metric, False


def _draw_overlay(
    image_path: Path,
    subject_bbox: Dict[str, float],
    crop_window: Dict[str, float],
    out_path: Path,
    label: str,
) -> None:
    with Image.open(image_path) as image:
        canvas = image.convert("RGB")
    draw = ImageDraw.Draw(canvas)

    x1, y1, x2, y2 = (
        float(subject_bbox["x1"]),
        float(subject_bbox["y1"]),
        float(subject_bbox["x2"]),
        float(subject_bbox["y2"]),
    )
    draw.rectangle((x1, y1, x2, y2), outline=(255, 0, 0), width=4)

    c1, c2 = float(crop_window["x"]), float(crop_window["y"])
    c3 = c1 + float(crop_window["width"])
    c4 = c2 + float(crop_window["height"])
    draw.rectangle((c1, c2, c3, c4), outline=(0, 120, 255), width=4)

    # Render label at top-left for readability in quick inspection.
    draw.text((12, 12), label, fill=(255, 255, 255))
    canvas.save(out_path)


def main() -> None:
    rows = []

    scenarios = {
        "original": {"x": 0, "y": 0, "width": "W", "height": "H"},
        "bad_left_crop": {"x": 0, "y": 0, "width": 300, "height": "H"},
    }

    for source in INPUT_IMAGES:
        rembg_path = REMBG_ROOT / f"{source.stem}_rembg.png"
        bbox_result = extract_subject_bbox_from_alpha(
            rembg_path,
            alpha_threshold=8,
            min_area=200,
            margin_ratio=0.01,
            component="largest",
        )
        if bbox_result.get("status") != "ok":
            rows.append({
                "image": source.name,
                "scenario": "error",
                "status": bbox_result.get("status", "failed"),
                "subject_crop_outside_ratio": "",
                "pass": "",
                "notes": bbox_result.get("reason", ""),
            })
            continue

        with Image.open(source) as source_image:
            src_w, src_h = source_image.size
        subject_bbox = bbox_result["primary_bbox_xyxy"]

        for label, window in scenarios.items():
            full_window = {
                "x": float(window["x"]),
                "y": float(window["y"]),
                "width": src_w if window["width"] == "W" else float(window["width"]),
                "height": src_h if window["height"] == "H" else float(window["height"]),
            }

            metric = _evaluate_subject_crop_guard(
                subject_bbox,
                (src_w, src_h),
                template_size=DEFAULT_CARD_CANVAS_SIZE,
                template_crop_window=full_window,
                max_subject_outside_ratio=SUBJECT_CROP_GUARD_MAX_SUBJECT_OUTSIDE_RATIO,
                metric_precision=SUBJECT_CROP_GUARD_METRIC_PRECISION,
            )

            rows.append({
                "image": source.name,
                "scenario": label,
                "subject_crop_outside_ratio": metric["subject_crop_outside_ratio"],
                "subject_crop_outside_ratio_in_template_frame": metric.get(
                    "subject_crop_outside_ratio_in_template_frame"
                ),
                "pass": metric["subject_crop_pass"],
                "crop_window": metric["source_crop_window"],
            })

            overlay_path = OUT_ROOT / f"{source.stem}_{label}.png"
            if label == "bad_left_crop":
                text = "FAIL scenario (bad crop)"
            else:
                text = "PASS scenario (original)"
            _draw_overlay(
                source,
                bbox_result["primary_bbox_xyxy"],
                full_window,
                overlay_path,
                text,
            )

        for scenario_name, target_min, target_max in RATIO_TARGETS:
            crop_window, metric, in_range = _find_crop_window_for_ratio(
                (src_w, src_h),
                subject_bbox,
                target_min,
                target_max,
            )
            rows.append({
                "image": source.name,
                "scenario": scenario_name,
                "target_range": f"{target_min:.2f}~{target_max:.2f}",
                "subject_crop_outside_ratio": metric.get("subject_crop_outside_ratio", ""),
                "subject_crop_outside_ratio_in_template_frame": metric.get(
                    "subject_crop_outside_ratio_in_template_frame", ""
                ),
                "pass": metric.get("subject_crop_pass", False),
                "crop_window": metric.get("source_crop_window", {}),
                "within_target": in_range,
            })

            ratio_in_frame = metric.get("subject_crop_outside_ratio_in_template_frame", "")
            overlay_path = OUT_ROOT / f"{source.stem}_{scenario_name}.png"
            _draw_overlay(
                source,
                bbox_result["primary_bbox_xyxy"],
                crop_window,
                overlay_path,
                f"{scenario_name} | target={target_min:.2f}~{target_max:.2f} | ratio={ratio_in_frame}",
            )

    print("== stage3_subject_crop_guard_results ==")
    print("threshold", SUBJECT_CROP_GUARD_MAX_SUBJECT_OUTSIDE_RATIO)
    if not rows:
        print("no rows")
        return

    headers = [
        "image",
        "scenario",
        "target_range",
        "outside_ratio",
        "outside_ratio_in_frame",
        "pass",
        "within_target",
        "crop_window",
    ]
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        print(
            f"| {row['image']} | {row['scenario']} | {row.get('target_range', '')} | "
            f"{row.get('subject_crop_outside_ratio', '')} | "
            f"{row.get('subject_crop_outside_ratio_in_template_frame', '')} | {row['pass']} | "
            f"{row.get('within_target', '')} | {row['crop_window']} |"
        )

    print(f"OVERLAYS={OUT_ROOT}")


if __name__ == "__main__":
    main()
