from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
W, H = 1080, 1350
FONT_REG = Path(r"C:\Windows\Fonts\malgun.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\malgunbd.ttf")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REG), size)


def cover_crop(path: Path, size=(W, H), focus_y=0.42) -> Image.Image:
    image = Image.open(path).convert("RGB")
    target_ratio = size[0] / size[1]
    ratio = image.width / image.height
    if ratio > target_ratio:
        crop_w = int(image.height * target_ratio)
        left = (image.width - crop_w) // 2
        image = image.crop((left, 0, left + crop_w, image.height))
    else:
        crop_h = int(image.width / target_ratio)
        top = max(0, min(image.height - crop_h, int((image.height - crop_h) * focus_y)))
        image = image.crop((0, top, image.width, top + crop_h))
    return image.resize(size, Image.Resampling.LANCZOS)


def fit_contain(path: Path, size: tuple[int, int], bg=(245, 244, 239)) -> Image.Image:
    image = Image.open(path).convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    out = Image.new("RGB", size, bg)
    out.paste(image, ((size[0] - image.width) // 2, (size[1] - image.height) // 2))
    return out


def gradient_overlay(image: Image.Image, top_alpha=10, bottom_alpha=225) -> Image.Image:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    px = overlay.load()
    for y in range(image.height):
        t = y / max(1, image.height - 1)
        a = int(top_alpha + (bottom_alpha - top_alpha) * (t ** 1.8))
        for x in range(image.width):
            px[x, y] = (0, 0, 0, a)
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for char in paragraph:
            trial = current + char
            if draw.textbbox((0, 0), trial, font=fnt)[2] <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = char
        if current:
            lines.append(current)
    return lines


def draw_text_block(draw, xy, text, fnt, fill, max_width, spacing=12, anchor="la"):
    x, y = xy
    lines = wrap(draw, text, fnt, max_width)
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill, anchor=anchor)
        y += fnt.size + spacing
    return y


def footer(draw: ImageDraw.ImageDraw, index: int, total: int, source: str, color=(238, 238, 232), dark=False):
    ink = (37, 36, 34) if dark else (244, 244, 240)
    draw.text((64, 52), f"ACCOUNT C  ·  {index:02d}/{total:02d}", font=font(24, True), fill=ink)
    draw.text((64, H - 68), source, font=font(19), fill=ink)
    draw.text((W - 64, H - 68), "내부 검토용 · 이미지 권리 미확인", font=font(18), fill=ink, anchor="ra")


def save_slide(image: Image.Image, out: Path, index: int):
    out.mkdir(parents=True, exist_ok=True)
    image.save(out / f"slide_{index:02d}.png", quality=95)


def fashion_slides() -> list[dict]:
    a = ROOT / "assets" / "fashion"
    out = ROOT / "fashion_dior_2027ss" / "slides"
    source = "자료·이미지: FashionN, DIOR MEN 2027 S/S 기사 (2026.06.25)"
    total = 10
    plan = [
        {"role": "cover", "media_type": "image", "headline": "익숙한 디올을\n다시 조립했다", "asset": "runway_13.png"},
        {"role": "concept", "media_type": "editorial", "headline": "이번 시즌의 문장\n친숙함의 재창조", "assets": ["runway_01.png", "runway_02.png"]},
        {"role": "silhouette", "media_type": "image", "headline": "먼저, 턱시도의\n크기가 달라졌다", "asset": "runway_18.png"},
        {"role": "material", "media_type": "comparison", "headline": "하운즈투스는\n짜지 않고 프린트했다", "assets": ["runway_13.png", "runway_14.png"]},
        {"role": "surface", "media_type": "image", "headline": "정장은 단정하게만\n끝나지 않는다", "asset": "runway_10.png"},
        {"role": "archive", "media_type": "editorial", "headline": "시대가 섞이는 방식", "assets": ["runway_07.png", "runway_09.png"]},
        {"role": "accessory", "media_type": "image", "headline": "가방까지\n같은 문법", "asset": "runway_06.png"},
        {"role": "palette", "media_type": "comparison", "headline": "색은 낮게,\n질감은 크게", "assets": ["runway_20.png", "runway_23.png"]},
        {"role": "sound", "media_type": "editorial", "headline": "음악도\n리믹스였다", "asset": "runway_24.png"},
        {"role": "editorial_close", "media_type": "image", "headline": "이 장면이 27 S/S를\n가장 잘 보여준다", "asset": "runway_10.png"},
    ]

    # 1 cover
    im = gradient_overlay(cover_crop(a / "runway_13.png"), 0, 235)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((64, 918, 438, 976), 29, fill=(208, 58, 44))
    d.text((88, 946), "DIOR MEN · 2027 S/S", font=font(24, True), fill="white", anchor="lm")
    draw_text_block(d, (64, 1010), plan[0]["headline"], font(78, True), "white", 900, 8)
    d.text((66, 1218), "친숙함을 버리지 않고, 다시 보게 만드는 방법", font=font(28), fill=(238, 235, 226))
    footer(d, 1, total, source)
    save_slide(im, out, 1)

    # 2 concept collage
    im = Image.new("RGB", (W, H), (235, 231, 220))
    im.paste(cover_crop(a / "runway_01.png", (520, 790), 0.4), (0, 0))
    im.paste(cover_crop(a / "runway_02.png", (560, 790), 0.4), (520, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 790, W, H), fill=(24, 24, 23))
    d.text((64, 856), "01  THE IDEA", font=font(24, True), fill=(210, 65, 49))
    draw_text_block(d, (64, 914), plan[1]["headline"], font(62, True), "white", 900, 8)
    draw_text_block(d, (64, 1088), "조나단 앤더슨은 관습을 비틀고, 서로 다른 시대의 아이디어를 한 장면 안에 겹쳤다.", font(30), (220, 217, 208), 900, 10)
    footer(d, 2, total, source)
    save_slide(im, out, 2)

    # 3 silhouette
    im = cover_crop(a / "runway_18.png")
    panel = Image.new("RGBA", (W, 475), (237, 232, 219, 242))
    im = im.convert("RGBA"); im.alpha_composite(panel, (0, 875)); im = im.convert("RGB")
    d = ImageDraw.Draw(im)
    d.text((64, 935), "02  SILHOUETTE", font=font(24, True), fill=(178, 45, 34))
    draw_text_block(d, (64, 990), plan[2]["headline"], font(56, True), (28, 27, 25), 900, 5)
    draw_text_block(d, (64, 1135), "몸을 조이는 격식 대신 어깨와 품을 넉넉하게. 클래식의 윤곽은 남기고 몸과의 거리를 바꿨다.", font(28), (60, 57, 52), 900, 8)
    footer(d, 3, total, source, dark=True)
    save_slide(im, out, 3)

    # 4 houndstooth comparison
    im = Image.new("RGB", (W, H), (247, 245, 239))
    im.paste(cover_crop(a / "runway_13.png", (540, 820), 0.42), (0, 0))
    im.paste(cover_crop(a / "runway_14.png", (540, 820), 0.42), (540, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 820, W, H), fill=(246, 243, 234))
    d.text((64, 878), "03  MATERIAL TRICK", font=font(24, True), fill=(178, 45, 34))
    draw_text_block(d, (64, 936), plan[3]["headline"], font(58, True), (29, 28, 26), 930, 5)
    draw_text_block(d, (64, 1095), "익숙한 체크를 그대로 복원하지 않았다. 직조처럼 보이지만 프린트로 구현해 ‘아는 것’과 ‘새로운 것’의 경계를 흔든다.", font(28), (65, 62, 57), 920, 8)
    footer(d, 4, total, source, dark=True)
    save_slide(im, out, 4)

    # 5 rough surface
    im = gradient_overlay(cover_crop(a / "runway_10.png"), 0, 235)
    d = ImageDraw.Draw(im)
    d.text((64, 850), "04  SURFACE", font=font(24, True), fill=(238, 80, 62))
    draw_text_block(d, (64, 914), plan[4]["headline"], font(62, True), "white", 870, 5)
    draw_text_block(d, (64, 1080), "풀린 실, 비대칭 레이어, 무너진 경계. 정교한 테일러링 위에 거친 표면을 겹쳐 긴장을 만들었다.", font(30), (236, 233, 225), 900, 9)
    footer(d, 5, total, source)
    save_slide(im, out, 5)

    # 6 archive
    im = Image.new("RGB", (W, H), (33, 31, 29))
    im.paste(cover_crop(a / "runway_07.png", (520, 860), 0.4), (0, 0))
    im.paste(cover_crop(a / "runway_09.png", (560, 860), 0.4), (520, 0))
    d = ImageDraw.Draw(im)
    d.text((64, 916), "05  ARCHIVE", font=font(24, True), fill=(229, 80, 60))
    d.text((64, 980), plan[5]["headline"], font=font(62, True), fill="white")
    draw_text_block(d, (64, 1085), "1979 오뜨 꾸뛰르의 트롱프뢰유 스카프 모티브까지 다시 호출했다. 복고를 복사한 것이 아니라 다른 시대의 기억을 현재 옷에 끼워 넣었다.", font(29), (224, 220, 210), 920, 9)
    footer(d, 6, total, source)
    save_slide(im, out, 6)

    # 7 accessory
    im = cover_crop(a / "runway_06.png")
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((560, 720, 1020, 1185), 28, fill=(244, 239, 226, 235), outline=(55, 52, 48), width=2)
    d.text((605, 780), "06  ACCESSORY", font=font(23, True), fill=(178, 45, 34))
    draw_text_block(d, (605, 840), plan[6]["headline"], font(56, True), (28, 27, 25), 360, 4)
    draw_text_block(d, (605, 985), "빈티지 블랭킷은 백으로, 까나쥬는 데님 토트로. 하우스의 표식을 다른 물성과 용도로 옮겼다.", font(27), (58, 54, 49), 360, 8)
    footer(d, 7, total, source, dark=True)
    save_slide(im, out, 7)

    # 8 palette
    im = Image.new("RGB", (W, H), (235, 232, 223))
    im.paste(cover_crop(a / "runway_20.png", (540, H), 0.38), (0, 0))
    im.paste(cover_crop(a / "runway_23.png", (540, H), 0.38), (540, 0))
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(overlay)
    od.rounded_rectangle((60, 870, 1020, 1232), 28, fill=(20, 20, 19, 220))
    im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(im)
    d.text((104, 930), "07  PALETTE & TEXTURE", font=font(23, True), fill=(236, 89, 68))
    draw_text_block(d, (104, 990), plan[7]["headline"], font(60, True), "white", 850, 5)
    draw_text_block(d, (104, 1130), "검정·갈색·청색처럼 낮은 색을 두고, 프린지·직조·광택처럼 표면의 차이를 크게 보이게 했다.", font(28), (226, 222, 213), 850, 8)
    footer(d, 8, total, source)
    save_slide(im, out, 8)

    # 9 sound
    im = cover_crop(a / "runway_24.png").filter(ImageFilter.GaussianBlur(10))
    im = gradient_overlay(im, 30, 210)
    d = ImageDraw.Draw(im)
    d.text((64, 240), "08  SOUND", font=font(24, True), fill=(241, 94, 70))
    draw_text_block(d, (64, 310), plan[8]["headline"], font(86, True), "white", 900, 8)
    d.rounded_rectangle((64, 585, 1016, 960), 32, fill=(245, 241, 229, 235))
    d.text((112, 652), "FRED AGAIN..  ×  DIOR", font=font(28, True), fill=(38, 36, 33))
    draw_text_block(d, (112, 730), "샘플링과 리믹싱으로 익숙한 음악에 새 의미를 붙인 커스텀 믹스. 옷의 ‘재조립’ 문법을 사운드까지 이어갔다.", font(34), (47, 44, 40), 840, 12)
    footer(d, 9, total, source)
    save_slide(im, out, 9)

    # 10 close
    im = gradient_overlay(cover_crop(a / "runway_10.png"), 0, 235)
    d = ImageDraw.Draw(im)
    d.text((64, 840), "EDITOR'S PICK", font=font(24, True), fill=(242, 93, 69))
    draw_text_block(d, (64, 905), plan[9]["headline"], font(60, True), "white", 900, 7)
    draw_text_block(d, (64, 1085), "정교한 테일러링 위에 거친 표면. 친숙함을 지우지 않고도 완전히 다르게 보이게 만든 이번 시즌의 핵심 장면이다.", font(30), (233, 230, 222), 900, 9)
    footer(d, 10, total, source)
    save_slide(im, out, 10)
    return plan


def beauty_slides() -> list[dict]:
    a = ROOT / "assets" / "beauty"
    out = ROOT / "beauty_summer_perfume" / "slides"
    source = "자료·이미지: Vogue Korea, 여름 향수 법칙 (2026.07.11)"
    total = 9
    plan = [
        {"role": "cover", "media_type": "image", "headline": "왜 내 향수만\n10분 만에 사라질까?", "asset": "beauty_04.jpg"},
        {"role": "mechanism", "media_type": "editorial", "headline": "땀만의 문제가 아니다", "asset": "beauty_01.jpg"},
        {"role": "data", "media_type": "editorial", "headline": "32°C", "asset": "beauty_02.jpg"},
        {"role": "note_green", "media_type": "image", "headline": "그린 & 아로마", "assets": ["beauty_02.jpg", "beauty_10.jpg"]},
        {"role": "note_musk", "media_type": "product", "headline": "화이트 머스크", "assets": ["beauty_05.jpg", "beauty_06.jpg"]},
        {"role": "note_woody", "media_type": "product", "headline": "가벼운 우디", "asset": "beauty_07.jpg"},
        {"role": "note_citrus", "media_type": "product", "headline": "시트러스의 함정", "asset": "beauty_08.jpeg"},
        {"role": "note_aqua", "media_type": "product", "headline": "아쿠아 & 오조닉", "assets": ["beauty_04.jpg", "beauty_09.jpeg"]},
        {"role": "checklist", "media_type": "editorial", "headline": "폭염 향수 체크", "asset": "beauty_03.jpg"},
    ]

    # 1 cover
    im = gradient_overlay(cover_crop(a / "beauty_04.jpg"), 0, 220)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((64, 70, 312, 125), 27, fill=(218, 255, 86))
    d.text((188, 98), "SUMMER BEAUTY", font=font(22, True), fill=(16, 43, 42), anchor="mm")
    draw_text_block(d, (64, 875), plan[0]["headline"], font(74, True), "white", 900, 9)
    d.text((66, 1100), "35℃, 향도 계절을 탄다", font=font(31), fill=(226, 255, 244))
    footer(d, 1, total, source)
    save_slide(im, out, 1)

    # 2 mechanism
    im = Image.new("RGB", (W, H), (239, 247, 240))
    im.paste(cover_crop(a / "beauty_01.jpg", (W, 720), 0.35), (0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((64, 665, 1016, 1240), 36, fill=(251, 250, 243))
    d.text((108, 730), "01  WHY", font=font(24, True), fill=(15, 105, 93))
    d.text((108, 790), plan[1]["headline"], font=font(60, True), fill=(20, 43, 40))
    draw_text_block(d, (108, 900), "높은 기온에 피부 pH·땀·피지 상태가 함께 달라진다. 같은 향수도 사람마다, 같은 사람도 시간대마다 다르게 느껴지는 이유다.", font(31), (52, 69, 65), 840, 10)
    d.rounded_rectangle((108, 1090, 880, 1165), 22, fill=(222, 246, 235))
    d.text((140, 1128), "건조한 피부는 향을 더 빨리 잃을 수 있다", font=font(27, True), fill=(14, 93, 82), anchor="lm")
    footer(d, 2, total, source, dark=True)
    save_slide(im, out, 2)

    # 3 stat
    im = cover_crop(a / "beauty_02.jpg").filter(ImageFilter.GaussianBlur(6))
    im = gradient_overlay(im, 30, 170)
    d = ImageDraw.Draw(im)
    d.text((64, 190), "VOGUE 기사에서 소개한 기준", font=font(27, True), fill=(223, 255, 117))
    d.text((64, 300), "32°C", font=font(160, True), fill="white")
    draw_text_block(d, (70, 520), "피부 온도가 이쯤 오르면\n향수는 서늘한 환경보다\n약 40% 빠르게 증발", font(54, True), "white", 900, 14)
    d.rounded_rectangle((64, 920, 1016, 1110), 28, fill=(18, 62, 57, 220))
    draw_text_block(d, (108, 975), "특히 시트러스·허브처럼 가벼운 톱 노트는 몇 분 만에 사라질 수 있다.", font(31), (232, 255, 247), 840, 10)
    footer(d, 3, total, source)
    save_slide(im, out, 3)

    # 4 green
    im = Image.new("RGB", (W, H), (232, 244, 222))
    im.paste(cover_crop(a / "beauty_02.jpg", (620, H), 0.35), (0, 0))
    product = fit_contain(a / "beauty_10.jpg", (390, 620), (246, 245, 237))
    im.paste(product, (650, 585))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((52, 70, 990, 420), 32, fill=(18, 64, 51, 225))
    d.text((96, 125), "02  HEAT-FRIENDLY NOTE", font=font(23, True), fill=(218, 255, 86))
    d.text((96, 190), plan[3]["headline"], font=font(64, True), fill="white")
    draw_text_block(d, (96, 295), "세이지·바질·로즈메리·녹차처럼 허브 중심 향조. 더위 속에서도 비교적 안정적이고 상쾌한 인상을 준다.", font(28), (228, 241, 232), 820, 8)
    d.text((680, 1220), "제품 예시: 끌로에 사블 라방드", font=font(22), fill=(35, 65, 55))
    footer(d, 4, total, source, dark=True)
    save_slide(im, out, 4)

    # 5 musk products
    im = Image.new("RGB", (W, H), (252, 244, 245))
    im.paste(fit_contain(a / "beauty_05.jpg", (460, 760), (252, 244, 245)), (60, 410))
    im.paste(fit_contain(a / "beauty_06.jpg", (460, 760), (252, 244, 245)), (560, 410))
    d = ImageDraw.Draw(im)
    d.text((64, 75), "03  CLEAN & LIGHT", font=font(24, True), fill=(190, 68, 94))
    d.text((64, 140), plan[4]["headline"], font=font(68, True), fill=(48, 39, 43))
    draw_text_block(d, (64, 255), "분자가 비교적 무거워 빠르게 증발하지 않고, 기온이 올라가도 부담스럽지 않은 향이 유지되는 쪽.", font(30), (89, 72, 78), 920, 9)
    d.text((90, 1185), "글로시에 유", font=font(24, True), fill=(88, 57, 69))
    d.text((590, 1185), "본투스탠드아웃 네이키드 런드리", font=font(24, True), fill=(88, 57, 69))
    footer(d, 5, total, source, dark=True)
    save_slide(im, out, 5)

    # 6 woody
    im = Image.new("RGB", (W, H), (230, 225, 205))
    im.paste(fit_contain(a / "beauty_07.jpg", (620, 1080), (230, 225, 205)), (420, 130))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((50, 100, 555, 1150), 36, fill=(55, 61, 39))
    d.text((94, 170), "04  STABLE NOTE", font=font(23, True), fill=(223, 248, 139))
    draw_text_block(d, (94, 245), plan[5]["headline"], font(72, True), "white", 400, 7)
    draw_text_block(d, (94, 500), "시더우드처럼 가벼운 우디 계열은 더위·습도·땀의 영향을 비교적 적게 받는다고 소개됐다.", font(31), (232, 234, 218), 400, 10)
    d.line((94, 790, 490, 790), fill=(175, 184, 134), width=2)
    draw_text_block(d, (94, 835), "피부의 열과 자연스럽게 어우러져 안정적인 잔향을 남기는 선택지.", font(28), (220, 224, 202), 400, 9)
    footer(d, 6, total, source, dark=True)
    save_slide(im, out, 6)

    # 7 citrus
    im = Image.new("RGB", (W, H), (255, 246, 206))
    im.paste(fit_contain(a / "beauty_08.jpeg", (560, 900), (255, 246, 206)), (480, 300))
    d = ImageDraw.Draw(im)
    d.text((64, 88), "05  WATCH OUT", font=font(24, True), fill=(210, 102, 0))
    draw_text_block(d, (64, 155), plan[6]["headline"], font(72, True), (44, 39, 27), 880, 7)
    draw_text_block(d, (64, 405), "레몬·라임·자몽 같은 청량감 때문에 여름에 먼저 손이 가지만, 휘발성이 높아 지속력은 짧아지기 쉽다.", font(31), (74, 64, 41), 380, 11)
    d.rounded_rectangle((64, 800, 430, 970), 24, fill=(255, 223, 93))
    d.text((96, 850), "청량감  ↑", font=font(35, True), fill=(72, 54, 12))
    d.text((96, 912), "지속력  ↓", font=font(35, True), fill=(72, 54, 12))
    footer(d, 7, total, source, dark=True)
    save_slide(im, out, 7)

    # 8 aqua
    im = cover_crop(a / "beauty_04.jpg")
    panel = Image.new("RGBA", (W, 560), (222, 248, 247, 235))
    im = im.convert("RGBA"); im.alpha_composite(panel, (0, 790)); im = im.convert("RGB")
    product = fit_contain(a / "beauty_09.jpeg", (300, 440), (222, 248, 247))
    im.paste(product, (715, 815))
    d = ImageDraw.Draw(im)
    d.text((64, 850), "06  HUMID WEATHER", font=font(23, True), fill=(0, 109, 128))
    draw_text_block(d, (64, 910), plan[7]["headline"], font(56, True), (12, 55, 65), 600, 4)
    draw_text_block(d, (64, 1050), "비·바다·맑은 공기를 떠올리는 향조. 습도가 높을수록 청량한 인상이 더 매력적으로 느껴지는 선택지다.", font(28), (38, 79, 86), 590, 8)
    footer(d, 8, total, source, dark=True)
    save_slide(im, out, 8)

    # 9 checklist
    im = gradient_overlay(cover_crop(a / "beauty_03.jpg"), 0, 225)
    d = ImageDraw.Draw(im)
    d.text((64, 150), "SAVE THIS", font=font(26, True), fill=(216, 255, 92))
    d.text((64, 215), plan[8]["headline"], font=font(72, True), fill="white")
    checks = [
        "향조보다 먼저, 더위에서 어떻게 변하는지",
        "피부가 건조하면 지속력이 짧아질 수 있음",
        "시트러스는 청량하지만 휘발성이 높음",
        "해변·수영장에서는 사용을 피하기",
    ]
    y = 390
    for i, line in enumerate(checks, 1):
        d.rounded_rectangle((64, y, 1016, y + 138), 28, fill=(245, 250, 241, 232))
        d.ellipse((94, y + 35, 158, y + 99), fill=(18, 111, 99))
        d.text((126, y + 67), str(i), font=font(28, True), fill="white", anchor="mm")
        d.text((190, y + 69), line, font=font(29, True), fill=(28, 58, 54), anchor="lm")
        y += 158
    d.text((64, 1060), "폭염엔 ‘좋아하는 향’보다 ‘더위에서 버티는 향’부터.", font=font(32, True), fill=(228, 255, 245))
    footer(d, 9, total, source)
    save_slide(im, out, 9)
    return plan


def contact_sheet(slide_dir: Path, output: Path, columns: int):
    files = sorted(slide_dir.glob("slide_*.png"))
    thumb_w = 270
    thumb_h = int(thumb_w * H / W)
    rows = (len(files) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * thumb_w, rows * (thumb_h + 36)), (232, 230, 224))
    draw = ImageDraw.Draw(canvas)
    for i, file in enumerate(files):
        image = Image.open(file).convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x, y = (i % columns) * thumb_w, (i // columns) * (thumb_h + 36)
        canvas.paste(image, (x, y))
        draw.text((x + 10, y + thumb_h + 6), file.stem.replace("slide_", "SLIDE "), font=font(18, True), fill=(30, 29, 27))
    canvas.save(output, quality=93)


def write_json(path: Path, value: dict):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_metadata(fashion_plan: list[dict], beauty_plan: list[dict]):
    common = {
        "review_only": True,
        "publishing_ready": False,
        "rights_status": "UNKNOWN_EDITORIAL_REUSE_NOT_CLEARED",
        "rights_note": "기사 페이지의 실제 이미지를 내부 데스크톱 검토 시안에만 사용. 게시·배포 전 이미지별 권리 확인 또는 사용권 확보 필요.",
        "generated_media_used": False,
        "fake_comments_used": False,
        "owner_review_target": "desktop",
    }
    fashion_dir = ROOT / "fashion_dior_2027ss"
    beauty_dir = ROOT / "beauty_summer_perfume"
    write_json(fashion_dir / "plan.json", {
        "schema_version": "cardnews_review_plan_v1",
        "account": "C_fashion_beauty",
        "category": "fashion",
        "topic": "DIOR MEN 2027 S/S — 친숙함의 재창조",
        "slide_count": len(fashion_plan),
        "editorial_mode": "official_concept_to_representative_looks",
        "forced_cta": False,
        "slides": fashion_plan,
        **common,
    })
    write_json(fashion_dir / "manifest.json", {
        **common,
        "primary_source": {
            "publisher": "FashionN",
            "url": "https://www.fashionn.com/board/read_new.php?number=61491&sel_cat=&table=1028",
            "published_at": "2026-06-25",
            "copyright_notice": "FashionN page states unauthorized reproduction/redistribution prohibited",
        },
        "content_basis": ["친숙함의 재창조", "오버사이즈 턱시도", "프린트 하운즈투스", "1979 꾸뛰르 모티브", "블랭킷·까나쥬 재해석", "Fred again.. 커스텀 믹스"],
        "production_gaps": ["공식 Dior 이미지 라이선스 미확인", "룩별 공식 번호 미확인", "게시용 원본 고해상도 확보 필요"],
    })
    write_json(beauty_dir / "plan.json", {
        "schema_version": "cardnews_review_plan_v1",
        "account": "C_fashion_beauty",
        "category": "beauty",
        "topic": "35℃ 여름 향수 법칙",
        "slide_count": len(beauty_plan),
        "editorial_mode": "seasonal_visual_practical_guide",
        "forced_cta": False,
        "slides": beauty_plan,
        **common,
    })
    write_json(beauty_dir / "manifest.json", {
        **common,
        "primary_source": {
            "publisher": "Vogue Korea",
            "url": "https://www.vogue.co.kr/2026/07/11/%EC%99%9C-%EB%82%B4-%ED%96%A5%EC%88%98%EB%8A%94-10%EB%B6%84-%EB%A7%8C%EC%97%90-%EC%82%AC%EB%9D%BC%EC%A7%88%EA%B9%8C-35%E2%84%83%EC%97%90%EB%8F%84-%EB%81%84%EB%96%A1%EC%97%86%EB%8A%94-%EC%97%AC/",
            "published_at": "2026-07-11",
            "commercial_disclosure": "Vogue article contains affiliate product links; this review package adds no affiliate link",
        },
        "content_basis": ["피부 온도와 증발", "피부 pH·피지·건조", "그린&아로마", "화이트 머스크", "가벼운 우디", "시트러스", "아쿠아&오조닉"],
        "production_gaps": ["기사·제품 이미지 라이선스 미확인", "기사의 약 40% 수치에 연결된 원 연구 출처 미확인", "제품 가격·재고·제휴 여부 미검증"],
    })


def write_index():
    html = """<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Account C 데스크톱 검토</title><style>
body{margin:0;background:#161616;color:#f4f1e8;font-family:'Malgun Gothic',sans-serif}header{padding:56px 5vw 30px;position:sticky;top:0;background:rgba(22,22,22,.94);backdrop-filter:blur(14px);z-index:2;border-bottom:1px solid #333}h1{margin:0;font-size:38px}.note{color:#bbb;margin-top:10px}.section{padding:42px 5vw 70px}.section h2{font-size:30px;margin:0 0 8px}.meta{color:#aaa;margin-bottom:28px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:22px}.card{margin:0}.card img{width:100%;aspect-ratio:4/5;object-fit:cover;border-radius:10px;box-shadow:0 18px 50px #0008}.card figcaption{padding:8px 2px;color:#aaa;font-size:13px}.fashion{border-top:6px solid #c6382c}.beauty{border-top:6px solid #c9f653}a{color:#d9ff76}</style></head><body>
<header><h1>ACCOUNT C · FASHION / BEAUTY</h1><div class=\"note\">2026-07-17 내부 검토용 · 이미지 권리 미확인 · 게시 불가</div></header>
<section class=\"section fashion\"><h2>FASHION · DIOR MEN 2027 S/S</h2><div class=\"meta\">10 slides · 공식 컨셉 → 대표 장면 → 실루엣·소재·연출 해설 · 강제 CTA 없음 · <a href=\"fashion_dior_2027ss/plan.json\">plan</a> / <a href=\"fashion_dior_2027ss/manifest.json\">manifest</a></div><div class=\"grid\">"""
    for i in range(1, 11):
        html += f'<figure class="card"><img loading="lazy" src="fashion_dior_2027ss/slides/slide_{i:02d}.png"><figcaption>FASHION · {i:02d}/10</figcaption></figure>'
    html += """</div></section><section class=\"section beauty\"><h2>BEAUTY · 35℃ 여름 향수 법칙</h2><div class=\"meta\">9 slides · 계절성·실용 정보 · 실제 제품·참조 이미지 중심 · <a href=\"beauty_summer_perfume/plan.json\">plan</a> / <a href=\"beauty_summer_perfume/manifest.json\">manifest</a></div><div class=\"grid\">"""
    for i in range(1, 10):
        html += f'<figure class="card"><img loading="lazy" src="beauty_summer_perfume/slides/slide_{i:02d}.png"><figcaption>BEAUTY · {i:02d}/09</figcaption></figure>'
    html += "</div></section></body></html>"
    (ROOT / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    fashion_plan = fashion_slides()
    beauty_plan = beauty_slides()
    contact_sheet(ROOT / "fashion_dior_2027ss" / "slides", ROOT / "fashion_dior_2027ss" / "contact_sheet.png", 5)
    contact_sheet(ROOT / "beauty_summer_perfume" / "slides", ROOT / "beauty_summer_perfume" / "contact_sheet.png", 5)
    write_metadata(fashion_plan, beauty_plan)
    write_index()
    print("account_c_review_package_completed")
