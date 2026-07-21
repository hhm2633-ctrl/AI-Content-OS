"""Render a publish-shaped local carousel from traced BLACK MONSTER FIT images.

The script performs local editorial composition only. It does not issue affiliate
links, call external APIs, or publish content.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.card_news.source_image_motion_montage import (
    render_source_image_motion_montage,
)


WIDTH = 1080
HEIGHT = 1350
INK = (18, 20, 22)
PAPER = (244, 244, 239)
WHITE = (255, 255, 255)
MUTED = (99, 103, 105)
LIME = (197, 255, 56)
BLUE = (86, 198, 255)


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def cover_crop(image: Image.Image, size: tuple[int, int], anchor: tuple[float, float] = (0.5, 0.5)) -> Image.Image:
    width, height = size
    scale = max(width / image.width, height / image.height)
    resized = image.resize((math.ceil(image.width * scale), math.ceil(image.height * scale)), Image.Resampling.LANCZOS)
    left = round((resized.width - width) * max(0.0, min(1.0, anchor[0])))
    top = round((resized.height - height) * max(0.0, min(1.0, anchor[1])))
    return resized.crop((left, top, left + width, top + height)).convert("RGB")


def gradient_overlay(image: Image.Image, top_alpha: int, bottom_alpha: int) -> Image.Image:
    base = image.convert("RGBA")
    overlay = Image.new("RGBA", base.size)
    pixels = overlay.load()
    for y in range(base.height):
        ratio = y / max(1, base.height - 1)
        alpha = round(top_alpha * (1 - ratio) + bottom_alpha * ratio)
        for x in range(base.width):
            pixels[x, y] = (5, 7, 9, alpha)
    return Image.alpha_composite(base, overlay).convert("RGB")


def wrap(draw: ImageDraw.ImageDraw, value: str, face: ImageFont.ImageFont, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in value.splitlines():
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for character in paragraph:
            candidate = current + character
            if current and draw.textbbox((0, 0), candidate, font=face)[2] > width:
                lines.append(current.rstrip())
                current = character.lstrip()
            else:
                current = candidate
        if current:
            lines.append(current)
    return lines


def multiline(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: str,
    face: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    width: int,
    *,
    spacing: int = 12,
    max_lines: int = 4,
) -> int:
    lines = wrap(draw, value, face, width)[:max_lines]
    x, y = xy
    height = face.getbbox("가Ay")[3] - face.getbbox("가Ay")[1]
    for line in lines:
        draw.text((x, y), line, font=face, fill=fill)
        y += height + spacing
    return y


def label(draw: ImageDraw.ImageDraw, value: str, *, dark: bool = True, page: int) -> None:
    fill = WHITE if dark else INK
    draw.text((64, 52), "STYLE / HEAT", font=font(24, bold=True), fill=fill)
    page_text = f"{page:02d} / 06"
    box = draw.textbbox((0, 0), page_text, font=font(22, bold=True))
    draw.text((WIDTH - 64 - (box[2] - box[0]), 54), page_text, font=font(22, bold=True), fill=fill)


def lower_copy(draw: ImageDraw.ImageDraw, body: str, *, dark: bool = True) -> None:
    color = (234, 236, 232) if dark else (71, 75, 77)
    draw.rectangle((0, 1184, WIDTH, HEIGHT), fill=(18, 20, 22) if dark else PAPER)
    draw.line((64, 1204, 1016, 1204), fill=LIME if dark else INK, width=4)
    multiline(draw, (64, 1230), body, font(28), color, 930, spacing=8, max_lines=2)


def rounded_image(canvas: Image.Image, source: Image.Image, box: tuple[int, int, int, int], anchor=(0.5, 0.5), radius: int = 34) -> None:
    left, top, right, bottom = box
    fitted = cover_crop(source, (right - left, bottom - top), anchor)
    mask = Image.new("L", fitted.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, fitted.width, fitted.height), radius=radius, fill=255)
    canvas.paste(fitted, (left, top), mask)


def slide_1(images: dict[str, Image.Image]) -> Image.Image:
    image = cover_crop(images["hero_gym"], (WIDTH, HEIGHT), (0.52, 0.28))
    image = gradient_overlay(ImageEnhance.Contrast(image).enhance(1.05), 55, 210)
    draw = ImageDraw.Draw(image)
    label(draw, "", page=1)
    draw.rounded_rectangle((64, 112, 302, 166), radius=27, fill=LIME)
    draw.text((88, 122), "SUMMER TRAINING", font=font(21, bold=True), fill=INK)
    multiline(draw, (64, 790), "운동 티셔츠,\n한 장이면 충분할까?", font(72, bold=True), WHITE, 900, spacing=7, max_lines=3)
    lower_copy(draw, "운동 뒤 바로 세탁한다면 기능보다 먼저 ‘몇 장을 돌려 입을지’를 보게 됩니다.")
    return image


def slide_2(images: dict[str, Image.Image]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    label(draw, "", dark=False, page=2)
    draw.text((64, 138), "운동용은", font=font(54, bold=True), fill=INK)
    draw.text((64, 205), "세탁 회전까지 본다", font=font(72, bold=True), fill=INK)
    cards = [
        ((64, 346, 368, 936), images["model_black_women"], "01", "입고"),
        ((388, 346, 692, 936), images["model_charcoal"], "02", "세탁하고"),
        ((712, 346, 1016, 936), images["model_white_women"], "03", "다시 입기"),
    ]
    for box, source, number, title in cards:
        rounded_image(image, source, box, (0.5, 0.33), 30)
        left, _, right, bottom = box
        draw.rounded_rectangle((left + 18, bottom - 92, right - 18, bottom - 22), radius=26, fill=(17, 19, 21, 235))
        draw.text((left + 38, bottom - 74), number, font=font(22, bold=True), fill=LIME)
        draw.text((left + 92, bottom - 75), title, font=font(25, bold=True), fill=WHITE)
    lower_copy(draw, "땀을 많이 흘리는 날엔 같은 옷의 반복 착용보다 여벌 구성이 더 실용적입니다.", dark=False)
    return image


def slide_3(images: dict[str, Image.Image]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(image)
    label(draw, "", dark=False, page=3)
    draw.text((64, 146), "그래서 고른", font=font(42, bold=True), fill=MUTED)
    multiline(draw, (64, 204), "무지 쿨론 반팔\n3장 세트", font(78, bold=True), INK, 700, spacing=5, max_lines=2)
    product = images["product_3pack"].convert("RGBA")
    scale = min(980 / product.width, 760 / product.height)
    product = product.resize((round(product.width * scale), round(product.height * scale)), Image.Resampling.LANCZOS)
    image.paste(product.convert("RGB"), ((WIDTH - product.width) // 2, 430))
    draw.rounded_rectangle((64, 1050, 1016, 1170), radius=30, fill=INK)
    draw.text((92, 1078), "BLACK", font=font(24, bold=True), fill=WHITE)
    draw.text((310, 1078), "CHARCOAL", font=font(24, bold=True), fill=(183, 186, 188))
    draw.text((636, 1078), "WHITE", font=font(24, bold=True), fill=WHITE)
    draw.ellipse((253, 1091, 273, 1111), fill=(28, 29, 30))
    draw.ellipse((574, 1091, 594, 1111), fill=(75, 77, 82))
    draw.ellipse((830, 1091, 850, 1111), fill=(244, 244, 240), outline=(160, 160, 160), width=2)
    lower_copy(draw, "블랙·차콜·화이트 세 가지 색을 한 세트로 묶은 운동용 무지 반팔입니다.", dark=False)
    return image


def slide_4(images: dict[str, Image.Image]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), (21, 23, 25))
    draw = ImageDraw.Draw(image)
    label(draw, "", page=4)
    rounded_image(image, images["model_black_men"], (64, 130, 652, 1115), (0.5, 0.22), 40)
    draw.rounded_rectangle((688, 130, 1016, 1115), radius=40, fill=(244, 244, 239))
    draw.text((728, 188), "ONE SET", font=font(22, bold=True), fill=MUTED)
    multiline(draw, (728, 246), "운동\n일상\n여벌", font(60, bold=True), INK, 250, spacing=20, max_lines=3)
    draw.line((728, 560, 956, 560), fill=INK, width=3)
    draw.text((728, 608), "3 PACK", font=font(56, bold=True), fill=INK)
    draw.rounded_rectangle((728, 704, 958, 766), radius=28, fill=LIME)
    draw.text((756, 720), "BLACK / CHARCOAL / WHITE", font=font(16, bold=True), fill=INK)
    multiline(draw, (728, 842), "한 장을 만능으로\n쓰는 대신, 상황별로\n돌려 입는 구성.", font(29, bold=True), INK, 242, spacing=10, max_lines=4)
    lower_copy(draw, "한 장을 만능으로 쓰기보다 운동·일상·여벌로 돌려 입는 구성을 보여줍니다.")
    return image


def slide_5(images: dict[str, Image.Image]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    label(draw, "", dark=False, page=5)
    draw.text((64, 142), "이런 사람에게", font=font(38, bold=True), fill=MUTED)
    draw.text((64, 202), "구성이 맞다", font=font(74, bold=True), fill=INK)
    rounded_image(image, images["color_fit_black"], (580, 120, 1016, 1140), (0.5, 0.22), 34)
    items = [
        ("01", "운동 뒤 바로 세탁하는 사람"),
        ("02", "주 3회 이상 운동하는 사람"),
        ("03", "색을 바꿔가며 돌려 입을 사람"),
    ]
    y = 390
    for number, copy in items:
        draw.rounded_rectangle((64, y, 522, y + 142), radius=30, fill=WHITE)
        draw.text((92, y + 29), number, font=font(25, bold=True), fill=(80, 145, 180))
        multiline(draw, (158, y + 25), copy, font(30, bold=True), INK, 330, spacing=5, max_lines=2)
        y += 166
    lower_copy(draw, "반대로 한 장만 필요하다면 3장 세트라는 이유만으로 고를 필요는 없습니다.", dark=False)
    return image


def slide_6(images: dict[str, Image.Image]) -> Image.Image:
    background = cover_crop(images["product_3pack"].filter(ImageFilter.GaussianBlur(2)), (WIDTH, HEIGHT), (0.5, 0.45))
    image = gradient_overlay(background, 120, 220)
    draw = ImageDraw.Draw(image)
    label(draw, "", page=6)
    draw.rounded_rectangle((64, 144, 1016, 1058), radius=54, fill=(18, 20, 22, 230), outline=(255, 255, 255), width=2)
    draw.text((112, 220), "3 PACK", font=font(26, bold=True), fill=LIME)
    multiline(draw, (112, 286), "블랙·차콜·화이트,\n뭐부터 입을래?", font(72, bold=True), WHITE, 830, spacing=8, max_lines=3)
    options = [("BLACK", (31, 32, 33)), ("CHARCOAL", (79, 81, 85)), ("WHITE", (239, 239, 233))]
    x = 112
    for title, color in options:
        draw.ellipse((x, 610, x + 92, 702), fill=color, outline=(180, 180, 180), width=2)
        draw.text((x, 736), title, font=font(21, bold=True), fill=WHITE)
        x += 274
    draw.line((112, 838, 968, 838), fill=(91, 95, 97), width=2)
    multiline(draw, (112, 886), "운동 빈도와 세탁 주기를 먼저 보고\n내 생활에 맞으면 그때 고르세요.", font(32, bold=True), (224, 226, 222), 800, spacing=8, max_lines=2)
    lower_copy(draw, "블랙·차콜·화이트 중 지금 가장 자주 손이 갈 색은 무엇인가요?")
    return image


def contact_sheet(slides: Sequence[Image.Image]) -> Image.Image:
    thumb_w, thumb_h = 270, 338
    gap = 26
    sheet = Image.new("RGB", (3 * thumb_w + 4 * gap, 2 * thumb_h + 3 * gap), (30, 32, 34))
    for index, slide in enumerate(slides):
        x = gap + (index % 3) * (thumb_w + gap)
        y = gap + (index // 3) * (thumb_h + gap)
        sheet.paste(slide.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS), (x, y))
    return sheet


def load_images(source_dir: Path) -> dict[str, Image.Image]:
    names = {
        "product_3pack": "product_3pack.webp",
        "hero_gym": "hero_gym.webp",
        "model_charcoal": "model_charcoal.webp",
        "model_black_women": "model_black_women.webp",
        "model_black_men": "model_black_men.webp",
        "model_white_women": "model_white_women.webp",
        "color_fit_black": "color_fit_black.webp",
        "detail_02": "detail_02.webp",
        "detail_06": "detail_06.webp",
    }
    return {key: Image.open(source_dir / filename).convert("RGB") for key, filename in names.items()}


def write_caption(output_dir: Path) -> None:
    caption = """운동 티셔츠는 한 장의 기능만큼 ‘몇 장을 돌려 입을지’도 중요합니다.

운동 뒤 바로 세탁하거나 주 3회 이상 운동한다면 블랙·차콜·화이트 3장 구성이 편할 수 있어요. 반대로 한 장만 필요하다면 세트라는 이유만으로 고를 필요는 없습니다.

제품: 블랙몬스터핏 3장 세트 드라이 쿨론 쿨티 기능성 쿨링 무지 반팔 운동 헬스 티셔츠

블랙·차콜·화이트 중 가장 자주 입을 색은?

이 포스팅은 네이버 쇼핑 커넥트 활동의 일환으로, 판매 발생 시 수수료를 제공받습니다.

상품 이미지: BLACK MONSTER FIT / MUSINSA 상품 페이지
"""
    (output_dir / "caption.txt").write_text(caption, encoding="utf-8")


def write_gallery(output_dir: Path) -> None:
    cards = "\n".join(
        f'<figure><img src="slides/slide_{index:02d}.png" alt="slide {index}"><figcaption>{index:02d}</figcaption></figure>'
        for index in range(1, 7)
    )
    html = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cooling Shirt Carousel</title><style>body{{margin:0;background:#121416;color:#fff;font-family:Arial,'Malgun Gothic',sans-serif}}main{{max-width:1400px;margin:auto;padding:40px}}h1{{font-size:28px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px}}figure{{margin:0}}img{{width:100%;display:block;border-radius:18px}}figcaption{{padding:8px 2px;color:#aeb3b5}}a{{color:#c5ff38}}</style></head><body><main><h1>폭염 운동용 3PACK 카드뉴스</h1><p>6 slides · 1080×1350 · local production preview</p><div class="grid">{cards}</div><p><a href="motion/slide_04_motion.mp4">4번 모션 슬라이드 보기</a></p><pre>{(output_dir / 'caption.txt').read_text(encoding='utf-8') if (output_dir / 'caption.txt').exists() else ''}</pre></main></body></html>"""
    (output_dir / "index.html").write_text(html, encoding="utf-8")


def render(source_dir: Path, output_dir: Path) -> dict[str, object]:
    slides_dir = output_dir / "slides"
    motion_dir = output_dir / "motion"
    slides_dir.mkdir(parents=True, exist_ok=True)
    motion_dir.mkdir(parents=True, exist_ok=True)
    images = load_images(source_dir)
    slides = [slide_1(images), slide_2(images), slide_3(images), slide_4(images), slide_5(images), slide_6(images)]
    for index, slide in enumerate(slides, start=1):
        slide.save(slides_dir / f"slide_{index:02d}.png", optimize=True)
    contact_sheet(slides).save(output_dir / "contact_sheet.jpg", quality=92, optimize=True)
    write_caption(output_dir)

    motion_sources = [
        ("model_black_men.webp", "https://global.musinsa.com/us/goods/3380690"),
        ("model_charcoal.webp", "https://global.musinsa.com/us/goods/3380690"),
        ("model_white_women.webp", "https://global.musinsa.com/us/goods/3380690"),
        ("product_3pack.webp", "https://global.musinsa.com/us/goods/3380690"),
    ]
    motion_result = render_source_image_motion_montage(
        [
            {
                "local_path": str(source_dir / filename),
                "source_url": url,
                "origin": "official",
                "rights_status": "public_product_page",
                "source_name": "BLACK MONSTER FIT / MUSINSA",
                "asset_id": f"blackmonsterfit-{index}",
            }
            for index, (filename, url) in enumerate(motion_sources, start=1)
        ],
        motion_dir / "slide_04_motion.mp4",
        width=1080,
        height=1350,
        fps=24,
        seconds_per_image=1.25,
        transition_seconds=0.24,
    )

    manifest = {
        "schema_version": "selected_cooling_shirt_carousel_v1",
        "status": "local_production_preview",
        "account": "C_fashion_beauty",
        "topic": "운동 빈도와 세탁 회전으로 고르는 3장 세트 기능성 반팔",
        "product_id": "813714789268755",
        "product_name": "블랙몬스터핏 3장 세트 드라이 쿨론 쿨티 기능성 쿨링 무지 반팔 운동 헬스 티셔츠",
        "slide_count": 6,
        "slide_size": [WIDTH, HEIGHT],
        "source_page": "https://global.musinsa.com/us/goods/3380690",
        "brandconnect_product_url": "https://brandconnect.naver.com/972943136654048/affiliate/products/813714789268755",
        "affiliate_link_issued": False,
        "publishing_executed": False,
        "price_claim_used": False,
        "review_claim_used": False,
        "motion": motion_result,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_gallery(output_dir)
    return manifest


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = render(args.source_dir, args.output_dir)
    print(json.dumps({"status": result["status"], "slide_count": result["slide_count"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
