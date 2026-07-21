"""Render the story-first V2 cooling-shirt carousel and one motion graphic.

This is local editorial production only. It does not issue affiliate links or publish.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from render_blackmonsterfit_cooling_carousel import (
    HEIGHT,
    INK,
    LIME,
    MUTED,
    PAPER,
    WHITE,
    WIDTH,
    contact_sheet,
    cover_crop,
    font,
    gradient_overlay,
    label,
    lower_copy,
    multiline,
    rounded_image,
)

ARTICLE_URL = "https://www.meconomynews.com/news/articleView.html?idxno=132893"
PRODUCT_URL = "https://global.musinsa.com/us/goods/3380690"
BRANDCONNECT_URL = "https://brandconnect.naver.com/972943136654048/affiliate/products/813714789268755"


def load_images(source_dir: Path) -> dict[str, Image.Image]:
    names = {
        "heat_scene": "ai_heatwave_commuter_v1.png",
        "gym_scene": "ai_same_model_gym_arrival_v1.png",
        "hero": "hero_gym.webp",
        "pack": "product_3pack.webp",
        "black_women": "model_black_women.webp",
        "black_men": "model_black_men.webp",
        "charcoal": "model_charcoal.webp",
        "white": "model_white_women.webp",
        "fit": "color_fit_black.webp",
    }
    return {key: Image.open(source_dir / name).convert("RGB") for key, name in names.items()}


def headline_badge(draw: ImageDraw.ImageDraw, value: str, *, x: int = 64, y: int = 122) -> None:
    face = font(22, bold=True)
    bounds = draw.textbbox((0, 0), value, font=face)
    width = bounds[2] - bounds[0] + 48
    draw.rounded_rectangle((x, y, x + width, y + 54), radius=27, fill=LIME)
    draw.text((x + 24, y + 12), value, font=face, fill=INK)


def ai_scene_label(draw: ImageDraw.ImageDraw, *, x: int = 64, y: int = 192) -> None:
    draw.rounded_rectangle((x, y, x + 172, y + 42), radius=21, fill=(18, 20, 22))
    draw.text((x + 20, y + 9), "AI 연출 이미지", font=font(18, bold=True), fill=WHITE)


def slide_1(images: dict[str, Image.Image]) -> Image.Image:
    image = cover_crop(images["heat_scene"], (WIDTH, HEIGHT), (0.58, 0.35))
    image = gradient_overlay(ImageEnhance.Contrast(image).enhance(1.04), 20, 220)
    draw = ImageDraw.Draw(image)
    label(draw, "", page=1)
    headline_badge(draw, "7월 17일 패션 뉴스")
    ai_scene_label(draw)
    multiline(draw, (64, 710), "폭염이 바꾼\n여름 옷차림", font(78, bold=True), WHITE, 900, spacing=4, max_lines=2)
    draw.text((68, 910), "반팔도 이제 ‘시원한가’부터 본다", font=font(36, bold=True), fill=LIME)
    lower_copy(draw, "길어진 더위 속에서 냉감·티셔츠 경쟁이 여름 패션의 중심으로 들어왔습니다.")
    return image


def slide_2(images: dict[str, Image.Image]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), (20, 22, 24))
    draw = ImageDraw.Draw(image)
    label(draw, "", page=2)
    rounded_image(image, images["heat_scene"], (64, 130, 518, 1115), (0.58, 0.30), 34)
    rounded_image(image, images["gym_scene"], (542, 130, 1016, 1115), (0.58, 0.30), 34)
    ai_scene_label(draw, y=144)
    draw.rounded_rectangle((92, 748, 988, 1054), radius=38, fill=(17, 19, 21))
    draw.text((128, 790), "출근길부터 땀나는데", font=font(39, bold=True), fill=WHITE)
    draw.text((128, 850), "퇴근 후 운동까지?", font=font(51, bold=True), fill=LIME)
    multiline(draw, (128, 932), "하루가 길어질수록 반팔 한 장으로\n계속 버티기 애매해집니다.", font(28, bold=True), WHITE, 790, spacing=7, max_lines=2)
    lower_copy(draw, "더위 뉴스가 실제 생활에서 닿는 지점은 ‘오늘 뭘 입고, 무엇을 갈아입을지’입니다.")
    return image


def slide_3(images: dict[str, Image.Image]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    label(draw, "", dark=False, page=3)
    draw.text((64, 142), "땀 난 운동복,", font=font(48, bold=True), fill=MUTED)
    multiline(draw, (64, 208), "다음 날 또\n집기 싫을 때", font(78, bold=True), INK, 650, spacing=4, max_lines=2)
    rounded_image(image, images["gym_scene"], (650, 120, 1016, 760), (0.62, 0.22), 36)
    ai_scene_label(draw, x=806, y=132)
    draw.rounded_rectangle((64, 690, 1016, 1120), radius=44, fill=WHITE)
    draw.text((106, 748), "거창한 기능보다", font=font(35, bold=True), fill=MUTED)
    draw.text((106, 810), "갈아입을 여벌이 먼저", font=font(56, bold=True), fill=INK)
    multiline(draw, (106, 905), "운동을 자주 하는 사람이라면\n한 장의 스펙보다 여벌 구성이 현실적일 수 있어요.", font(29), INK, 820, spacing=8, max_lines=2)
    lower_copy(draw, "모든 사람에게 세트가 필요한 건 아닙니다. 자주 갈아입는 사람에게만 이유가 생깁니다.", dark=False)
    return image


def slide_4(images: dict[str, Image.Image]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(image)
    label(draw, "", dark=False, page=4)
    headline_badge(draw, "여벌이 필요했다면")
    multiline(draw, (64, 212), "그래서 본 건\n기본색 3장", font(76, bold=True), INK, 850, spacing=4, max_lines=2)
    product = images["pack"]
    product = cover_crop(product, (930, 610), (0.5, 0.5))
    image.paste(product, (75, 462))
    draw.rounded_rectangle((120, 1002, 960, 1140), radius=34, fill=INK)
    draw.text((168, 1042), "BLACK", font=font(25, bold=True), fill=WHITE)
    draw.text((421, 1042), "CHARCOAL", font=font(25, bold=True), fill=(185, 188, 190))
    draw.text((766, 1042), "WHITE", font=font(25, bold=True), fill=WHITE)
    lower_copy(draw, "블랙·차콜·화이트를 한 번에 묶은 무지 반팔 3장 구성입니다.", dark=False)
    return image


def slide_5(images: dict[str, Image.Image]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), (19, 21, 23))
    draw = ImageDraw.Draw(image)
    label(draw, "", page=5)
    draw.text((64, 130), "운동하는 날", font=font(54, bold=True), fill=WHITE)
    draw.text((64, 198), "많이 걷는 날", font=font(54, bold=True), fill=LIME)
    draw.text((64, 266), "가방에 여벌 두는 날", font=font(54, bold=True), fill=WHITE)
    cards = [
        ((64, 382, 354, 1092), images["black_men"], "BLACK"),
        ((395, 382, 685, 1092), images["charcoal"], "CHARCOAL"),
        ((726, 382, 1016, 1092), images["white"], "WHITE"),
    ]
    for box, source, title in cards:
        rounded_image(image, source, box, (0.5, 0.27), 28)
        left, _, right, bottom = box
        draw.rounded_rectangle((left + 18, bottom - 72, right - 18, bottom - 18), radius=24, fill=(17, 19, 21))
        bounds = draw.textbbox((0, 0), title, font=font(21, bold=True))
        draw.text(((left + right - (bounds[2] - bounds[0])) / 2, bottom - 58), title, font=font(21, bold=True), fill=WHITE)
    lower_copy(draw, "색마다 용도를 정해두기보다 그날 옷과 상황에 맞춰 바꿔 입는 쪽이 자연스럽습니다.")
    return image


def slide_6(images: dict[str, Image.Image]) -> Image.Image:
    background = cover_crop(images["hero"].filter(ImageFilter.GaussianBlur(2.5)), (WIDTH, HEIGHT), (0.52, 0.25))
    image = gradient_overlay(background, 150, 230)
    draw = ImageDraw.Draw(image)
    label(draw, "", page=6)
    draw.rounded_rectangle((64, 150, 1016, 1060), radius=48, fill=(18, 20, 22))
    draw.text((112, 218), "내 생활에 맞는 쪽은?", font=font(30, bold=True), fill=LIME)
    multiline(draw, (112, 290), "여벌이 필요하면 3장", font(58, bold=True), WHITE, 820, spacing=4, max_lines=1)
    multiline(draw, (112, 392), "한 장이면 충분하면\n굳이 세트까지", font(58, bold=True), (190, 194, 196), 820, spacing=6, max_lines=2)
    draw.line((112, 600, 968, 600), fill=(91, 95, 97), width=2)
    multiline(draw, (112, 658), "운동복, 한 장만 사는 편?\n여벌까지 두는 편?", font(47, bold=True), WHITE, 820, spacing=12, max_lines=2)
    draw.rounded_rectangle((112, 886, 968, 962), radius=34, fill=LIME)
    draw.text((170, 907), "상품보다 먼저, 내 사용 빈도를 보세요", font=font(29, bold=True), fill=INK)
    lower_copy(draw, "판매 페이지의 ‘드라이·쿨링’ 표현은 상품명 기준이며 별도 성능을 단정하지 않습니다.")
    return image


def ease_out(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return 1 - (1 - value) ** 3


def motion_frame(images: dict[str, Image.Image], frame: int, fps: int) -> Image.Image:
    t = frame / fps
    canvas = Image.new("RGB", (WIDTH, HEIGHT), (16, 18, 20))
    draw = ImageDraw.Draw(canvas)
    if t < 2.4:
        zoom = 1.0 + 0.035 * (t / 2.4)
        heat_scene = cover_crop(images["heat_scene"], (round(WIDTH / zoom), round(HEIGHT / zoom)), (0.58, 0.34))
        heat_scene = heat_scene.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        canvas.paste(gradient_overlay(heat_scene, 10, 210), (0, 0))
        draw = ImageDraw.Draw(canvas)
        p = ease_out(t / 0.55)
        draw.rounded_rectangle((64, int(130 + (1 - p) * 80), 340, int(184 + (1 - p) * 80)), radius=27, fill=LIME)
        draw.text((90, int(142 + (1 - p) * 80)), "7월 17일 패션 뉴스", font=font(21, bold=True), fill=INK)
        if t > 0.35:
            ai_scene_label(draw, y=int(202 + (1 - p) * 80))
        q = ease_out(max(0.0, t - 0.35) / 0.7)
        y = int(760 + (1 - q) * 170)
        multiline(draw, (64, y), "폭염이 바꾼\n여름 옷차림", font(82, bold=True), WHITE, 900, spacing=4, max_lines=2)
        if t > 1.25:
            r = ease_out((t - 1.25) / 0.65)
            draw.line((66, 965, int(66 + 900 * r), 965), fill=LIME, width=8)
            draw.text((68, 990), "반팔도 ‘시원한가’부터", font=font(39, bold=True), fill=LIME)
    elif t < 4.6:
        local = t - 2.4
        left = cover_crop(images["heat_scene"], (WIDTH // 2, HEIGHT), (0.58, 0.30))
        right = cover_crop(images["gym_scene"], (WIDTH // 2, HEIGHT), (0.58, 0.30))
        canvas.paste(left, (0, 0))
        wipe = int((WIDTH // 2) * ease_out(local / 0.6))
        canvas.paste(right.crop((0, 0, wipe, HEIGHT)), (WIDTH // 2, 0))
        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rectangle((0, 690, WIDTH, HEIGHT), fill=(12, 14, 16, 205))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(canvas)
        p = ease_out(max(0.0, local - 0.35) / 0.55)
        x = int(64 - (1 - p) * 180)
        draw.text((x, 760), "출근길부터 땀나는데", font=font(42, bold=True), fill=WHITE)
        draw.text((x, 828), "퇴근 후 운동까지?", font=font(54, bold=True), fill=LIME)
        draw.text((x, 918), "반팔 한 장으로 계속 버티기 애매한 날", font=font(31, bold=True), fill=WHITE)
    else:
        local = t - 4.6
        canvas = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
        draw = ImageDraw.Draw(canvas)
        draw.text((64, 90), "그래서 본 건", font=font(42, bold=True), fill=MUTED)
        draw.text((64, 148), "기본색 3장", font=font(76, bold=True), fill=INK)
        panels = [(images["black_men"], 64), (images["charcoal"], 390), (images["white"], 716)]
        for index, (source, target_x) in enumerate(panels):
            start = index * 0.18
            p = ease_out(max(0.0, local - start) / 0.55)
            x = int(target_x + (1 - p) * (WIDTH + 180))
            crop = cover_crop(source, (300, 810), (0.5, 0.25))
            canvas.paste(crop, (x, 300))
        if local > 0.9:
            p = ease_out((local - 0.9) / 0.55)
            draw.rounded_rectangle((64, int(1145 + (1 - p) * 120), 1016, int(1260 + (1 - p) * 120)), radius=34, fill=INK)
            draw.text((118, int(1178 + (1 - p) * 120)), "여벌이 필요한 사람에게만 이유가 생긴다", font=font(34, bold=True), fill=WHITE)
    return canvas


def render_motion(images: dict[str, Image.Image], output_path: Path) -> dict[str, object]:
    fps, seconds = 24, 7.0
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="heat_story_frames_", dir=output_path.parent) as temp:
        frame_dir = Path(temp)
        for index in range(round(fps * seconds)):
            motion_frame(images, index, fps).save(frame_dir / f"frame_{index:04d}.jpg", quality=90)
        command = [
            ffmpeg, "-y", "-loglevel", "error", "-framerate", str(fps),
            "-i", str(frame_dir / "frame_%04d.jpg"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(output_path),
        ]
        subprocess.run(command, check=True)
    return {
        "status": "motion_graphic_ready",
        "format_label": "editorial_motion_graphic_not_source_footage",
        "duration_seconds": seconds,
        "fps": fps,
        "output_path": str(output_path),
        "information_changes": ["news_headline_reveal", "news_to_daily_scene", "product_reveal"],
    }


def write_caption(output_dir: Path) -> None:
    text = """폭염이 길어지면서 여름 반팔을 고르는 기준도 달라지고 있습니다. 7월 17일 패션 뉴스에서도 냉감 소재와 티셔츠 경쟁이 주요 흐름으로 다뤄졌습니다.

출근 뒤 운동까지 이어지는 날처럼 자주 갈아입는 사람이라면 한 장의 스펙보다 여벌 구성이 더 현실적일 수 있어요. 그래서 블랙·차콜·화이트 3장으로 묶인 무지 반팔을 함께 봤습니다. 반대로 한 장이면 충분한 사람은 굳이 세트를 고를 필요가 없습니다.

제품: 블랙몬스터핏 3장 세트 드라이 쿨론 쿨티 기능성 쿨링 무지 반팔 운동 헬스 티셔츠

운동복, 한 장만 사는 편인가요? 여벌까지 두는 편인가요?

이 포스팅은 네이버 쇼핑 커넥트 활동의 일환으로, 판매 발생 시 수수료를 제공받습니다.

참고: 시장경제 「폭염이 바꾼 여름 패션 공식」(2026.07.17)
상품 이미지: BLACK MONSTER FIT / MUSINSA 상품 페이지
"""
    (output_dir / "caption.txt").write_text(text, encoding="utf-8")


def write_gallery(output_dir: Path) -> None:
    cards = "\n".join(
        f'<figure><img src="slides/slide_{index:02d}.png" alt="slide {index}"><figcaption>{index:02d}</figcaption></figure>'
        for index in range(1, 7)
    )
    caption = (output_dir / "caption.txt").read_text(encoding="utf-8")
    html = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Heatwave Story Carousel V2</title><style>body{{margin:0;background:#121416;color:#fff;font-family:Arial,'Malgun Gothic',sans-serif}}main{{max-width:1400px;margin:auto;padding:40px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px}}figure{{margin:0}}img{{width:100%;display:block;border-radius:18px}}figcaption{{padding:8px 2px;color:#aeb3b5}}a{{color:#c5ff38}}pre{{white-space:pre-wrap;background:#1d2022;padding:24px;border-radius:18px}}</style></head><body><main><h1>폭염 이슈 → 생활 장면 → 상품 V2</h1><div class="grid">{cards}</div><p><a href="motion/heatwave_to_product_motion.mp4">7초 모션그래픽 보기</a></p><pre>{caption}</pre></main></body></html>"""
    (output_dir / "index.html").write_text(html, encoding="utf-8")


def render(source_dir: Path, output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    slides_dir = output_dir / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)
    images = load_images(source_dir)
    slides = [slide_1(images), slide_2(images), slide_3(images), slide_4(images), slide_5(images), slide_6(images)]
    for index, slide in enumerate(slides, 1):
        slide.save(slides_dir / f"slide_{index:02d}.png", optimize=True)
    contact_sheet(slides).save(output_dir / "contact_sheet.jpg", quality=92, optimize=True)
    motion = render_motion(images, output_dir / "motion" / "heatwave_to_product_motion.mp4")
    write_caption(output_dir)
    manifest = {
        "schema_version": "heatwave_commerce_story_carousel_v2",
        "status": "local_production_preview",
        "account": "C_fashion_beauty",
        "focus": "same_day_fashion_issue_to_real_life_need_to_product",
        "story_order": ["news_issue", "daily_scene", "need", "product_reveal", "use_scenes", "choice"],
        "article": {"title": "폭염이 바꾼 여름 패션 공식… 냉감·티셔츠·라이트 포멀 경쟁", "published_at": "2026-07-17T11:58:42+09:00", "url": ARTICLE_URL},
        "article_image_used": False,
        "celebrity_assets_used": False,
        "auxiliary_ai_scene": {
            "file": "source_media/ai_heatwave_commuter_v1.png",
            "role": "fictional_heatwave_lifestyle_reenactment",
            "public_label": "AI 연출 이미지",
            "evidence_role": False,
            "celebrity_likeness_requested": False,
        },
        "product_id": "813714789268755",
        "product_url": PRODUCT_URL,
        "brandconnect_product_url": BRANDCONNECT_URL,
        "affiliate_link_issued": False,
        "publishing_executed": False,
        "unsupported_performance_claims_used": False,
        "motion": motion,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_gallery(output_dir)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(render(args.source_dir, args.output_dir), ensure_ascii=False))


if __name__ == "__main__":
    main()
