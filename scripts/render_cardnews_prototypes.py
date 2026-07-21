"""Render local-review CardNews prototypes without touching the protected workflow.

These previews deliberately render missing/blocked evidence as a visible gap. They are not
publishing assets and must never be used to impersonate real comments, screenshots, source
footage, brand products, or licensed runway photography.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.common.external_storage import resolve_external_path  # noqa: E402

CANVAS = 1080
PROTOTYPE_SUBDIR = ("cardnews_prototypes", "2026-07-16")
STORAGE_CONFIG = REPO_ROOT / "config" / "source_data_storage.json"


def default_prototype_root() -> Path:
    """Return the configured heavy-artifact root without creating it."""
    return resolve_external_path(
        "artifacts", *PROTOTYPE_SUBDIR, config_path=STORAGE_CONFIG
    )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument(
        "--out", "--output-root", dest="output_root", type=Path, default=None
    )
    return parser.parse_args(argv)


def resolve_cli_paths(args: argparse.Namespace) -> Tuple[Path, Path]:
    if args.root is not None and args.output_root is not None:
        return args.root, args.output_root
    default_root = default_prototype_root()
    root = args.root if args.root is not None else default_root
    out_dir = args.output_root if args.output_root is not None else default_root / "previews"
    return root, out_dir


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = [
        "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def text(value: Any) -> str:
    return str(value or "").strip()


def slide_role(slide: Dict[str, Any]) -> str:
    return text(slide.get("slide_role") or slide.get("role") or "editorial")


def media_type(slide: Dict[str, Any]) -> str:
    return text(slide.get("media_type") or "editorial")


def account_identity(plan: Dict[str, Any]) -> str:
    return text(plan.get("account_id") or plan.get("account") or plan.get("prototype_id"))


def slide_copy(slide: Dict[str, Any]) -> Tuple[str, str]:
    copy_block = slide.get("copy") if isinstance(slide.get("copy"), dict) else {}
    headline = text(
        slide.get("headline")
        or copy_block.get("headline")
        or slide.get("title")
    )
    body = text(
        slide.get("body")
        or copy_block.get("body")
        or slide.get("caption")
        or slide.get("dialogue")
    )
    return headline, body


def wrapped(draw: ImageDraw.ImageDraw, value: str, face: ImageFont.ImageFont, width: int) -> List[str]:
    result: List[str] = []
    for paragraph in value.splitlines() or [value]:
        words = paragraph.split()
        if not words:
            result.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if draw.textbbox((0, 0), candidate, font=face)[2] <= width:
                current = candidate
            else:
                result.append(current)
                current = word
        result.append(current)
    return result


def multiline(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[int, int],
    value: str,
    face: ImageFont.ImageFont,
    fill: Tuple[int, int, int],
    width: int,
    spacing: int = 12,
    max_lines: int = 4,
) -> int:
    lines = wrapped(draw, value, face, width)[:max_lines]
    if len(wrapped(draw, value, face, width)) > max_lines and lines:
        lines[-1] = lines[-1].rstrip("…") + "…"
    x, y = xy
    line_height = face.getbbox("가Ay")[3] - face.getbbox("가Ay")[1]
    for line in lines:
        draw.text((x, y), line, font=face, fill=fill)
        y += line_height + spacing
    return y


def gradient(top: Tuple[int, int, int], bottom: Tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGB", (CANVAS, CANVAS), top)
    pixels = image.load()
    for y in range(CANVAS):
        ratio = y / max(CANVAS - 1, 1)
        color = tuple(int(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(3))
        for x in range(CANVAS):
            pixels[x, y] = color
    return image


def draw_person(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, color: Tuple[int, int, int]) -> None:
    head = int(56 * scale)
    draw.ellipse((x - head, y - head, x + head, y + head), fill=color)
    shoulder = int(130 * scale)
    body_h = int(250 * scale)
    draw.rounded_rectangle((x - shoulder, y + head - 8, x + shoulder, y + body_h), radius=55, fill=color)


def draw_incident_visual(draw: ImageDraw.ImageDraw, slide: Dict[str, Any], index: int) -> None:
    role = slide_role(slide)
    draw.rectangle((0, 0, CANVAS, 610), fill=(18, 18, 20))
    draw.polygon([(0, 520), (CANVAS, 250), (CANVAS, 610), (0, 610)], fill=(75, 9, 16))
    for offset in range(0, 1080, 120):
        draw.line((offset, 120, offset + 320, 500), fill=(48, 48, 52), width=4)
    if "comment" in role:
        draw.rounded_rectangle((105, 115, 975, 505), radius=36, fill=(245, 242, 236))
        draw.ellipse((145, 160, 205, 220), fill=(180, 180, 180))
        draw.text((235, 162), "실제 댓글 영역", font=font(34, True), fill=(25, 25, 25))
        draw.text((145, 270), "댓글 본문이 아직 수집되지 않아\n자리만 예약했습니다.", font=font(38), fill=(60, 60, 60), spacing=16)
        draw.rounded_rectangle((145, 410, 545, 464), radius=22, fill=(215, 215, 215))
        draw.text((165, 417), "가짜 댓글 생성 금지", font=font(26, True), fill=(95, 0, 0))
    elif "conflict" in role:
        draw.rectangle((105, 115, 450, 475), fill=(38, 40, 44), outline=(245, 245, 240), width=6)
        for row in range(3):
            for col in range(3):
                x = 145 + col * 95
                y = 155 + row * 95
                draw.rectangle((x, y, x + 55, y + 55), fill=(212, 202, 175) if (row + col) % 2 else (90, 92, 96))
        draw.line((610, 115, 515, 300, 645, 300, 540, 500), fill=(238, 52, 72), width=22)
    elif "escalation" in role:
        for radius in (70, 135, 205):
            draw.arc((540 - radius, 300 - radius, 540 + radius, 300 + radius), 210, 510, fill=(238, 52, 72), width=18)
        draw.polygon([(510, 215), (585, 300), (510, 385)], fill=(245, 245, 240))
        draw.text((95, 440), "갈등 → 폭행·협박", font=font(55, True), fill=(245, 245, 240))
    elif "claim" in role:
        draw.text((95, 90), "“", font=font(230, True), fill=(238, 52, 72))
        draw.rounded_rectangle((260, 145, 925, 455), radius=38, fill=(244, 241, 233))
        draw.text((315, 205), "피해 주민 주장", font=font(48, True), fill=(32, 32, 34))
        draw.text((315, 290), "경찰 대응 때문에\n피해가 커졌다", font=font(38), fill=(74, 65, 62), spacing=14)
    elif "evidence" in role:
        draw.rounded_rectangle((115, 105, 965, 495), radius=38, fill=(244, 241, 233))
        for row, (label, checked) in enumerate((("수사 착수", True), ("경찰 공식 입장", False), ("법적 처분", False))):
            y = 155 + row * 105
            draw.rounded_rectangle((165, y, 220, y + 55), radius=10, outline=(75, 9, 16), width=5)
            if checked:
                draw.line((177, y + 28, 191, y + 43, 212, y + 12), fill=(117, 15, 26), width=7)
            draw.text((255, y + 4), label, font=font(38, True), fill=(32, 32, 34))
    elif "cta" in role:
        draw.rounded_rectangle((95, 130, 495, 460), radius=42, fill=(244, 241, 233))
        draw.rounded_rectangle((585, 130, 985, 460), radius=42, fill=(117, 15, 26), outline=(244, 241, 233), width=6)
        draw.text((185, 255), "충분", font=font(62, True), fill=(32, 32, 34))
        draw.text((670, 255), "부족", font=font(62, True), fill=(245, 245, 240))
    else:
        draw_person(draw, 690, 250, 1.1, (12, 12, 14))
        draw.ellipse((165, 115, 410, 360), outline=(238, 52, 72), width=16)
        draw.line((335, 315, 505, 480), fill=(238, 52, 72), width=16)
        draw.text((95, 470), f"CASE {index:02d}", font=font(70, True), fill=(245, 245, 240))


def draw_story_visual(draw: ImageDraw.ImageDraw, slide: Dict[str, Any], index: int) -> None:
    role = slide_role(slide)
    draw.rounded_rectangle((45, 45, 1035, 700), radius=26, fill=(255, 249, 236), outline=(35, 31, 28), width=8)
    if "comment" in role:
        draw.rounded_rectangle((130, 110, 950, 570), radius=45, fill=(255, 255, 255), outline=(35, 31, 28), width=5)
        draw.text((180, 170), "실제 댓글 미수집", font=font(44, True), fill=(35, 31, 28))
        draw.text((180, 260), "152개 반응 수만 확인됨\n본문 확보 전 인용하지 않음", font=font(38), fill=(85, 75, 68), spacing=18)
    elif "cover" in role:
        draw.rounded_rectangle((115, 105, 430, 510), radius=28, fill=(255, 255, 255), outline=(35, 31, 28), width=5)
        draw.rectangle((115, 105, 430, 185), fill=(225, 137, 148))
        draw.text((190, 118), "WEDDING", font=font(30, True), fill=(255, 255, 255))
        draw.ellipse((190, 260, 280, 350), outline=(35, 31, 28), width=8)
        draw.ellipse((265, 260, 355, 350), outline=(35, 31, 28), width=8)
        draw.line((520, 305, 900, 305), fill=(35, 31, 28), width=14)
        draw.line((685, 250, 745, 360), fill=(225, 137, 148), width=18)
        draw.line((745, 250, 685, 360), fill=(225, 137, 148), width=18)
    elif "known" in role:
        draw.line((540, 60, 540, 685), fill=(35, 31, 28), width=5)
        draw_person(draw, 300, 330, 0.8, (225, 137, 148))
        draw_person(draw, 770, 330, 0.8, (225, 137, 148))
        draw.text((210, 115), "30대", font=font(40, True), fill=(35, 31, 28))
        draw.text((680, 115), "자매", font=font(40, True), fill=(35, 31, 28))
    elif "conflict" in role:
        draw_person(draw, 300, 340, 0.72, (225, 137, 148))
        draw_person(draw, 790, 340, 0.72, (81, 96, 128))
        draw.polygon([(540, 125), (485, 315), (570, 285), (515, 535), (645, 250), (565, 275)], fill=(235, 176, 45))
    elif "escalation" in role:
        draw.rounded_rectangle((350, 95, 730, 590), radius=55, fill=(42, 45, 51), outline=(35, 31, 28), width=8)
        draw.rounded_rectangle((385, 155, 695, 500), radius=25, fill=(246, 246, 243))
        draw.text((445, 250), "읽지 않음", font=font(45, True), fill=(115, 115, 115))
        draw.line((430, 390, 650, 390), fill=(225, 137, 148), width=12)
    elif "deadline" in role:
        draw.rounded_rectangle((105, 105, 500, 555), radius=32, fill=(255, 255, 255), outline=(35, 31, 28), width=6)
        draw.rectangle((105, 105, 500, 200), fill=(225, 137, 148))
        draw.text((210, 125), "D-DAY", font=font(42, True), fill=(255, 255, 255))
        draw.text((205, 280), "얼마\n남지 않음", font=font(58, True), fill=(35, 31, 28), spacing=14)
        draw.rounded_rectangle((650, 220, 900, 520), radius=35, outline=(81, 96, 128), width=12)
        draw.text((695, 340), "빈자리", font=font(40, True), fill=(81, 96, 128))
    elif "gap" in role:
        for row in range(2):
            for col in range(2):
                x = 115 + col * 445
                y = 105 + row * 255
                draw.rounded_rectangle((x, y, x + 390, y + 205), radius=28, fill=(255, 255, 255), outline=(35, 31, 28), width=4)
                draw.text((x + 35, y + 45), "?", font=font(80, True), fill=(225, 137, 148))
    elif "cta" in role:
        draw.ellipse((320, 165, 520, 365), outline=(225, 137, 148), width=18)
        draw.ellipse((475, 165, 675, 365), outline=(81, 96, 128), width=18)
        draw.line((210, 470, 870, 470), fill=(35, 31, 28), width=12)
        draw.line((500, 415, 575, 525), fill=(225, 137, 148), width=18)
        draw.line((575, 415, 500, 525), fill=(225, 137, 148), width=18)
    else:
        draw_person(draw, 300, 330, 0.8, (225, 137, 148))
        draw_person(draw, 770, 330, 0.8, (81, 96, 128))
    draw.text((80, 620), "실제 사연 바탕 · 세부 장면은 확인 후 재구성", font=font(26, True), fill=(90, 77, 67))


def draw_fashion_visual(draw: ImageDraw.ImageDraw, slide: Dict[str, Any], index: int) -> None:
    role = slide_role(slide)
    draw.rectangle((0, 0, CANVAS, CANVAS), fill=(228, 225, 214))
    draw.polygon([(0, 0), (760, 0), (420, 1080), (0, 1080)], fill=(35, 38, 39))
    accent = [(207, 40, 52), (226, 215, 183), (65, 109, 142), (231, 231, 226)][index % 4]
    if role in {"save_summary", "debate_cta"}:
        for column in range(3):
            left = 90 + column * 315
            draw.rounded_rectangle((left, 150, left + 265, 650), radius=24, fill=(244, 241, 231), outline=(35, 38, 39), width=4)
            draw_person(draw, left + 132, 320, 0.55, accent if column == 1 else (90, 92, 90))
    else:
        x = 650 if index % 2 else 720
        draw.ellipse((x - 78, 95, x + 78, 251), fill=(208, 179, 151))
        draw.polygon([(x - 145, 245), (x + 145, 245), (x + 205, 855), (x - 190, 855)], fill=accent)
        draw.polygon([(x - 190, 855), (x - 35, 855), (x - 95, 1040), (x - 230, 1040)], fill=(30, 32, 34))
        draw.polygon([(x + 30, 855), (x + 205, 855), (x + 235, 1040), (x + 95, 1040)], fill=(30, 32, 34))
        draw.line((80, 185, 430, 185), fill=accent, width=12)
        draw.text((80, 100), "EDITORIAL STUDY", font=font(31, True), fill=(244, 241, 231))


def palette(account_id: str) -> Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]:
    if "account_a" in account_id:
        return (15, 15, 17), (117, 15, 26), (248, 245, 238)
    if "account_b" in account_id:
        return (250, 238, 215), (224, 120, 136), (35, 31, 28)
    return (227, 224, 212), (202, 42, 52), (24, 26, 26)


def render_slide(plan: Dict[str, Any], slide: Dict[str, Any], index: int) -> Image.Image:
    account_id = account_identity(plan)
    bg, accent, ink = palette(account_id)
    image = Image.new("RGB", (CANVAS, CANVAS), bg)
    draw = ImageDraw.Draw(image)
    if "account_a" in account_id:
        draw_incident_visual(draw, slide, index)
    elif "account_b" in account_id:
        draw_story_visual(draw, slide, index)
    else:
        draw_fashion_visual(draw, slide, index)

    # The prototype copy band is deliberately compact. Fashion stays image-first.
    band_top = 675 if "account_b" in account_id else 640
    if "account_a" in account_id:
        band_fill = (248, 245, 238)
        title_fill = (22, 22, 24)
        body_fill = (82, 72, 67)
    elif "account_b" in account_id:
        band_fill = (255, 249, 236)
        title_fill = ink
        body_fill = (92, 77, 68)
    else:
        band_fill = (242, 239, 229)
        title_fill = ink
        body_fill = (78, 77, 72)
    draw.rounded_rectangle((52, band_top, 1028, 1016), radius=34, fill=band_fill)
    draw.rectangle((82, band_top + 42, 96, band_top + 132), fill=accent)

    role = slide_role(slide).upper().replace("_", " ")
    draw.text((120, band_top + 42), role, font=font(24, True), fill=accent)
    headline, body = slide_copy(slide)
    end_y = multiline(draw, (120, band_top + 86), headline, font(58, True), title_fill, 820, 8, 3)
    if body:
        multiline(draw, (120, min(end_y + 18, 900)), body, font(30), body_fill, 820, 8, 2)

    page = int(slide.get("page") or slide.get("slide_number") or index)
    draw.text((890, 70), f"{page:02d}", font=font(34, True), fill=accent if "account_b" not in account_id else ink)
    source = plan.get("source") if isinstance(plan.get("source"), dict) else {}
    if not source and isinstance(plan.get("source_evidence"), dict):
        source = plan["source_evidence"]
    publisher = text(source.get("publisher") or slide.get("source_credit") or "source pending")
    draw.text((70, 1032), f"LOCAL PROTOTYPE · NOT FOR PUBLISH · {publisher[:42]}", font=font(20, True), fill=(105, 100, 94))
    return image


def load_plans(root: Path) -> Iterable[Tuple[Path, Dict[str, Any]]]:
    for path in sorted(root.glob("account_*/plan.json")):
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict) and isinstance(payload.get("slides"), list):
            yield path, payload


def contact_sheet(images: List[Image.Image], labels: List[str]) -> Image.Image:
    columns = 4
    thumb = 250
    gap = 22
    header = 70
    rows = math.ceil(len(images) / columns)
    sheet = Image.new("RGB", (columns * (thumb + gap) + gap, header + rows * (thumb + 55)), (24, 24, 26))
    draw = ImageDraw.Draw(sheet)
    draw.text((gap, 18), "VARIABLE CAROUSEL · LOCAL REVIEW CONTACT SHEET", font=font(26, True), fill=(245, 243, 237))
    for i, image in enumerate(images):
        x = gap + (i % columns) * (thumb + gap)
        y = header + (i // columns) * (thumb + 55)
        sheet.paste(image.resize((thumb, thumb), Image.Resampling.LANCZOS), (x, y))
        draw.text((x, y + thumb + 10), labels[i][:28], font=font(18, True), fill=(225, 221, 213))
    return sheet


def run(root: Path, out_dir: Path) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: Dict[str, Any] = {
        "schema_version": "cardnews_prototype_render_manifest_v1",
        "status": "local_review_only",
        "publishing_ready": False,
        "accounts": [],
    }
    for path, plan in load_plans(root):
        account_id = account_identity(plan) or path.parent.name
        account_dir = out_dir / path.parent.name
        account_dir.mkdir(parents=True, exist_ok=True)
        rendered: List[Image.Image] = []
        labels: List[str] = []
        outputs: List[str] = []
        for index, slide in enumerate(plan["slides"], start=1):
            if not isinstance(slide, dict):
                continue
            image = render_slide(plan, slide, index)
            output = account_dir / f"slide_{index:02d}.png"
            image.save(output, optimize=True)
            rendered.append(image)
            labels.append(f"{index:02d} {slide_role(slide)}")
            outputs.append(output.as_posix())
        sheet_path = account_dir / "contact_sheet.png"
        if rendered:
            contact_sheet(rendered, labels).save(sheet_path, optimize=True)
        manifest["accounts"].append(
            {
                "account_id": account_id,
                "plan_path": path.as_posix(),
                "slide_count": len(rendered),
                "outputs": outputs,
                "contact_sheet": sheet_path.as_posix() if rendered else None,
                "limits": plan.get("known_limitations", []),
            }
        )
    manifest_path = root / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    return manifest


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    root, out_dir = resolve_cli_paths(args)
    result = run(root, out_dir)
    print(json.dumps({"status": result["status"], "accounts": len(result["accounts"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
