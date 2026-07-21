"""Render two 4:5 motion-card samples from still images only.

The script creates motion through camera moves, crossfades, editorial graphics,
and lightweight particles. It does not download sources or publish anything.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional, Sequence

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.common.external_storage import resolve_external_path  # noqa: E402

WIDTH = 1080
HEIGHT = 1350
FPS = 30
RESAMPLE = Image.Resampling.LANCZOS
FONT_REGULAR = Path("C:/Windows/Fonts/malgun.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")
STORAGE_CONFIG = REPO_ROOT / "config" / "source_data_storage.json"
MOTION_OUTPUT_SUBDIR = ("cardnews_motion_samples", "no_source_video")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=None)
    return parser.parse_args(argv)


def resolve_output_root(output_root: Optional[Path]) -> Path:
    if output_root is not None:
        return output_root
    return resolve_external_path(
        "artifacts", *MOTION_OUTPUT_SUBDIR, config_path=STORAGE_CONFIG
    )


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size=size)


def ease(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def open_rgb(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return image.convert("RGB")


def cover_motion(
    image: Image.Image,
    progress: float,
    zoom_start: float = 1.0,
    zoom_end: float = 1.08,
    pan_x: float = 0.0,
    pan_y: float = 0.0,
) -> Image.Image:
    progress = ease(progress)
    zoom = zoom_start + (zoom_end - zoom_start) * progress
    base_scale = max(WIDTH / image.width, HEIGHT / image.height)
    scale = base_scale * zoom
    resized = image.resize(
        (max(WIDTH, int(image.width * scale)), max(HEIGHT, int(image.height * scale))),
        RESAMPLE,
    )
    excess_x = resized.width - WIDTH
    excess_y = resized.height - HEIGHT
    center_x = excess_x / 2 + pan_x * (progress - 0.5) * excess_x
    center_y = excess_y / 2 + pan_y * (progress - 0.5) * excess_y
    left = int(max(0, min(excess_x, center_x)))
    top = int(max(0, min(excess_y, center_y)))
    return resized.crop((left, top, left + WIDTH, top + HEIGHT))


def darken_bottom(image: Image.Image, strength: int = 210, start: int = 760) -> Image.Image:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    span = max(1, HEIGHT - start)
    for y in range(start, HEIGHT):
        alpha = int(strength * ((y - start) / span) ** 1.4)
        draw.line((0, y, WIDTH, y), fill=(0, 0, 0, alpha), width=1)
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def draw_label(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, color: tuple[int, int, int]) -> None:
    label_font = font(26, True)
    box = draw.textbbox((x, y), text, font=label_font)
    draw.rounded_rectangle((box[0] - 18, box[1] - 10, box[2] + 18, box[3] + 10), 18, fill=color)
    draw.text((x, y), text, font=label_font, fill="white")


def draw_shadow_text(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    text: str,
    text_font: ImageFont.FreeTypeFont,
    fill: str = "white",
    anchor: str | None = None,
    spacing: int = 8,
) -> None:
    x, y = position
    draw.multiline_text(
        (x + 3, y + 5), text, font=text_font, fill=(0, 0, 0, 180),
        anchor=anchor, spacing=spacing, align="left"
    )
    draw.multiline_text(
        (x, y), text, font=text_font, fill=fill,
        anchor=anchor, spacing=spacing, align="left"
    )


Scene = Callable[[float, float], Image.Image]


def render_timeline(scenes: list[tuple[float, float, Scene]], time_value: float, fade: float = 0.22) -> Image.Image:
    for index, (start, end, renderer) in enumerate(scenes):
        if start <= time_value < end or index == len(scenes) - 1:
            local = max(0.0, min(1.0, (time_value - start) / max(0.001, end - start)))
            current = renderer(local, time_value)
            if index < len(scenes) - 1 and time_value >= end - fade:
                next_renderer = scenes[index + 1][2]
                mix = ease((time_value - (end - fade)) / fade)
                return Image.blend(current, next_renderer(0.0, time_value), mix)
            return current
    return scenes[-1][2](1.0, time_value)


def encode_video(output: Path, duration: float, frame_renderer: Callable[[float], Image.Image]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}",
        "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264",
        "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert process.stdin is not None
    try:
        for frame_index in range(round(duration * FPS)):
            time_value = frame_index / FPS
            frame = frame_renderer(time_value).convert("RGB")
            process.stdin.write(frame.tobytes())
    finally:
        process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError(f"FFmpeg failed while encoding {output}")


def news_sample(asset_root: Path, output: Path) -> None:
    lead = open_rgb(asset_root / "news/assets/ytn_lead.jpg")
    arrest = open_rgb(asset_root / "news/assets/newsis_arrest.jpg")

    def lead_scene(progress: float, _: float) -> Image.Image:
        image = darken_bottom(cover_motion(lead, progress, 1.02, 1.18, pan_x=-0.18), 225, 670)
        draw = ImageDraw.Draw(image, "RGBA")
        draw_label(draw, "NEWS", 64, 72, (228, 38, 52))
        draw_shadow_text(draw, (64, 910), "형사과장까지\n구속영장", font(82, True), spacing=2)
        draw.text((66, 1110), "광주 광산경찰서 수사 확대", font=font(35), fill=(225, 230, 238))
        return image

    def map_scene(progress: float, time_value: float) -> Image.Image:
        image = Image.new("RGB", (WIDTH, HEIGHT), "#07111f")
        draw = ImageDraw.Draw(image, "RGBA")
        for x in range(0, WIDTH, 90):
            draw.line((x, 0, x, HEIGHT), fill=(43, 82, 120, 70), width=1)
        for y in range(0, HEIGHT, 90):
            draw.line((0, y, WIDTH, y), fill=(43, 82, 120, 70), width=1)
        draw.text((64, 72), "LOCATION", font=font(26, True), fill=(104, 185, 255))
        draw_shadow_text(draw, (64, 142), "광주광역시", font(67, True))
        start = (220, 670)
        end = (780, 480)
        line_progress = ease(min(1.0, progress * 1.5))
        now = (int(start[0] + (end[0] - start[0]) * line_progress), int(start[1] + (end[1] - start[1]) * line_progress))
        draw.line((start[0], start[1], now[0], now[1]), fill=(74, 168, 255), width=9)
        draw.ellipse((start[0] - 13, start[1] - 13, start[0] + 13, start[1] + 13), fill=(255, 255, 255))
        pulse = 18 + int(35 * (0.5 + 0.5 * math.sin(time_value * 12)))
        draw.ellipse((end[0] - pulse, end[1] - pulse, end[0] + pulse, end[1] + pulse), outline=(255, 72, 82, 210), width=8)
        draw.ellipse((end[0] - 12, end[1] - 12, end[0] + 12, end[1] + 12), fill=(255, 72, 82))
        draw.text((end[0] - 40, end[1] + 74), "광산구", font=font(48, True), fill="white", anchor="ma")
        draw.text((64, 1110), "수사의 초점이 위로 올라갔다", font=font(43, True), fill=(220, 230, 242))
        return image

    def arrest_scene(progress: float, _: float) -> Image.Image:
        image = darken_bottom(cover_motion(arrest, progress, 1.04, 1.15, pan_x=0.25), 225, 830)
        draw = ImageDraw.Draw(image, "RGBA")
        draw.rounded_rectangle((70, 890, 1010, 1160), 28, fill=(5, 10, 18, 220))
        draw.line((190, 1020, 890, 1020), fill=(173, 189, 207), width=5)
        for x, label in ((220, "7/8\n구속"), (540, "7/15\n송치"), (860, "영장\n청구")):
            draw.ellipse((x - 15, 1005, x + 15, 1035), fill=(235, 48, 62))
            draw.multiline_text((x, 1055), label, font=font(34, True), fill="white", anchor="ma", align="center", spacing=4)
        return image

    def apology_scene(progress: float, _: float) -> Image.Image:
        image = darken_bottom(cover_motion(lead, progress, 1.12, 1.28, pan_x=0.16), 235, 600)
        image = ImageEnhance.Color(image).enhance(0.7)
        draw = ImageDraw.Draw(image, "RGBA")
        draw_label(draw, "THE TURN", 64, 74, (228, 38, 52))
        draw_shadow_text(draw, (64, 820), "강력팀장,\n유족에 사과", font(76, True), spacing=4)
        return image

    def org_scene(progress: float, _: float) -> Image.Image:
        image = Image.new("RGB", (WIDTH, HEIGHT), "#0a0c11")
        draw = ImageDraw.Draw(image, "RGBA")
        draw.text((64, 72), "INVESTIGATION", font=font(25, True), fill=(235, 61, 72))
        draw_shadow_text(draw, (64, 140), "수사, 윗선으로", font(74, True))
        labels = ["경찰서장", "형사과장", "강력팀장"]
        for index, label in enumerate(labels):
            y = 450 + index * 235
            reveal = ease(max(0.0, min(1.0, progress * 2.2 - index * 0.35)))
            width = int(760 * reveal)
            draw.rounded_rectangle((120, y, 120 + width, y + 120), 26, fill=(26, 33, 44), outline=(235, 61, 72), width=4)
            if reveal > 0.55:
                draw.text((160, y + 60), label, font=font(47, True), fill="white", anchor="lm")
            if index < 2:
                draw.line((500, y + 120, 500, y + 235), fill=(235, 61, 72), width=5)
        return image

    scenes = [
        (0.0, 1.5, lead_scene),
        (1.5, 2.7, map_scene),
        (2.7, 4.3, arrest_scene),
        (4.3, 5.7, apology_scene),
        (5.7, 7.0, org_scene),
    ]
    encode_video(output, 7.0, lambda time_value: render_timeline(scenes, time_value))


def dior_sample(asset_root: Path, output: Path) -> None:
    mood = open_rgb(asset_root / "dior/assets/generated_almond_orchard_mood.png")
    almond = open_rgb(asset_root / "dior/assets/official_almond.jpg")
    ingredients = open_rgb(asset_root / "dior/assets/official_ingredients.jpg")
    bottle = open_rgb(asset_root / "dior/assets/official_bottle.jpg")
    pack = open_rgb(asset_root / "dior/assets/official_pack.jpg")

    def particles(image: Image.Image, time_value: float, color: tuple[int, int, int]) -> Image.Image:
        layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer, "RGBA")
        for index in range(34):
            x = (index * 193 + int(time_value * (18 + index % 7))) % WIDTH
            y = (index * 277 - int(time_value * (24 + index % 5))) % HEIGHT
            radius = 2 + index % 5
            alpha = 45 + (index * 13) % 95
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*color, alpha))
        return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")

    def mood_scene(progress: float, time_value: float) -> Image.Image:
        image = particles(cover_motion(mood, progress, 1.02, 1.13, pan_x=0.25), time_value, (255, 241, 198))
        image = darken_bottom(image, 165, 850)
        draw = ImageDraw.Draw(image, "RGBA")
        draw.text((64, 74), "SOUTH OF FRANCE", font=font(25, True), fill=(255, 245, 218))
        draw_shadow_text(draw, (64, 1030), "남프랑스의\n아몬드 과수원", font(67, True), spacing=2)
        return image

    def almond_scene(progress: float, time_value: float) -> Image.Image:
        image = particles(cover_motion(almond, progress, 1.03, 1.2, pan_y=-0.2), time_value, (255, 229, 156))
        draw = ImageDraw.Draw(image, "RGBA")
        draw.rounded_rectangle((60, 78, 405, 147), 18, fill=(240, 235, 209, 220))
        draw.text((82, 91), "BITTER ALMOND", font=font(29, True), fill=(35, 40, 30))
        return image

    def ingredient_scene(progress: float, time_value: float) -> Image.Image:
        image = particles(cover_motion(ingredients, progress, 1.03, 1.17, pan_x=-0.2), time_value, (255, 239, 194))
        image = darken_bottom(image, 130, 900)
        draw = ImageDraw.Draw(image, "RGBA")
        draw_shadow_text(draw, (64, 1090), "만다린의 빛\n아몬드의 쓸쓸한 단맛", font(50, True), spacing=2)
        return image

    def bottle_scene(progress: float, time_value: float) -> Image.Image:
        image = cover_motion(bottle, progress, 1.02, 1.15, pan_x=0.16)
        image = particles(image, time_value, (255, 207, 95))
        flare = Image.new("RGBA", image.size, (0, 0, 0, 0))
        flare_draw = ImageDraw.Draw(flare, "RGBA")
        flare_x = int(130 + progress * 920)
        for radius in range(120, 5, -12):
            alpha = max(0, int(3.2 * (120 - radius)))
            flare_draw.ellipse((flare_x - radius, 770 - radius, flare_x + radius, 770 + radius), fill=(255, 210, 98, min(28, alpha)))
        return Image.alpha_composite(image.convert("RGBA"), flare).convert("RGB")

    def pack_scene(progress: float, time_value: float) -> Image.Image:
        image = particles(cover_motion(pack, progress, 1.03, 1.1), time_value, (255, 225, 138))
        image = darken_bottom(image, 190, 840)
        draw = ImageDraw.Draw(image, "RGBA")
        draw_shadow_text(draw, (64, 1010), "DIOR PARADISE", font(70, True))
        draw.text((66, 1110), "남프랑스의 여름을 한 병에", font=font(37), fill=(248, 244, 235))
        return image

    scenes = [
        (0.0, 1.45, mood_scene),
        (1.45, 2.8, almond_scene),
        (2.8, 4.15, ingredient_scene),
        (4.15, 5.75, bottle_scene),
        (5.75, 7.2, pack_scene),
    ]
    encode_video(output, 7.2, lambda time_value: render_timeline(scenes, time_value, fade=0.28))


def write_manifest(output_root: Path) -> None:
    manifest = {
        "schema_version": "cardnews_no_source_video_samples_v1",
        "outputs": [
            {
                "topic_id": "A-IC-05",
                "file": "news/gwangsan_police_motion.mp4",
                "method": "actual_news_stills_plus_self_authored_motion_graphics",
                "sources": [
                    "https://www.ytn.co.kr/_ln/0115_202607162241017867",
                    "https://mobile.newsis.com/view/NISX20260715_0003710186",
                ],
            },
            {
                "topic_id": "C-P15",
                "file": "dior/dior_paradise_motion.mp4",
                "method": "official_dior_stills_plus_generated_auxiliary_mood_plate",
                "sources": [
                    "https://www.dior.com/en_us/beauty/page/summer-animation-lcp.html",
                ],
                "generated_auxiliary_asset": "dior/assets/generated_almond_orchard_mood.png",
            },
        ],
    }
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    output_root = resolve_output_root(args.output_root).resolve()
    news_sample(args.asset_root.resolve(), output_root / "news/gwangsan_police_motion.mp4")
    dior_sample(args.asset_root.resolve(), output_root / "dior/dior_paradise_motion.mp4")
    write_manifest(output_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
