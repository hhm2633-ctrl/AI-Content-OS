from __future__ import annotations

import html
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
W, H = 1080, 1350
FONT_REG = Path(r"C:\Windows\Fonts\malgun.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\malgunbd.ttf")
TODAY = "2026.07.17"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REG), size)


def cover_crop(path: Path, size: tuple[int, int] = (W, H), focus_y: float = 0.5) -> Image.Image:
    image = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    target = size[0] / size[1]
    ratio = image.width / image.height
    if ratio > target:
        crop_w = int(image.height * target)
        left = (image.width - crop_w) // 2
        image = image.crop((left, 0, left + crop_w, image.height))
    else:
        crop_h = int(image.width / target)
        top = int((image.height - crop_h) * focus_y)
        top = max(0, min(image.height - crop_h, top))
        image = image.crop((0, top, image.width, top + crop_h))
    return image.resize(size, Image.Resampling.LANCZOS)


def instagram_media_crop(path: Path, size: tuple[int, int] = (W, H)) -> Image.Image:
    image = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    # The owner-provided captures are 1440x2825 Instagram screens. This crop keeps
    # the carousel media and removes most app chrome/caption areas without altering evidence.
    left, top, right, bottom = 0, 485, image.width, min(image.height, 2285)
    media = image.crop((left, top, right, bottom))
    return cover_crop_from_image(media, size)


def cover_crop_from_image(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target = size[0] / size[1]
    ratio = image.width / image.height
    if ratio > target:
        crop_w = int(image.height * target)
        left = (image.width - crop_w) // 2
        image = image.crop((left, 0, left + crop_w, image.height))
    else:
        crop_h = int(image.width / target)
        top = max(0, (image.height - crop_h) // 2)
        image = image.crop((0, top, image.width, top + crop_h))
    return image.resize(size, Image.Resampling.LANCZOS)


def darken_bottom(image: Image.Image, start: float = 0.48, max_alpha: int = 230) -> Image.Image:
    base = image.convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    px = overlay.load()
    start_y = int(H * start)
    for y in range(start_y, H):
        t = (y - start_y) / max(1, H - start_y)
        alpha = int(max_alpha * (t ** 1.45))
        for x in range(W):
            px[x, y] = (0, 0, 0, alpha)
    return Image.alpha_composite(base, overlay).convert("RGB")


def text_lines(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
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


def draw_multiline(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fnt: ImageFont.FreeTypeFont,
                   fill: str | tuple[int, int, int], max_width: int, spacing: int = 8) -> int:
    x, y = xy
    for line in text_lines(draw, text, fnt, max_width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += fnt.size + spacing
    return y


def card(path: Path, account: str, index: int, total: int, headline: str, subline: str, source: str,
         accent: str, *, screenshot: bool = False, label: str = "", focus_y: float = 0.5,
         headline_size: int = 66, start: float = 0.46) -> Image.Image:
    image = instagram_media_crop(path) if screenshot else cover_crop(path, focus_y=focus_y)
    image = ImageEnhance.Contrast(image).enhance(1.04)
    image = darken_bottom(image, start=start, max_alpha=238)
    draw = ImageDraw.Draw(image)
    draw.text((58, 46), f"ACCOUNT {account}  ·  {TODAY}", font=font(22, True), fill="white")
    draw.text((W - 58, 46), f"{index:02d}/{total:02d}", font=font(22, True), fill="white", anchor="ra")
    y = 835
    if label:
        box = draw.textbbox((0, 0), label, font=font(21, True))
        box_w = box[2] - box[0] + 42
        draw.rounded_rectangle((58, y, 58 + box_w, y + 50), 25, fill=accent)
        draw.text((79, y + 25), label, font=font(21, True), fill="white", anchor="lm")
        y += 78
    y = draw_multiline(draw, (58, y), headline, font(headline_size, True), "white", 950, 8)
    if subline:
        y += 18
        draw_multiline(draw, (60, y), subline, font(28), (236, 236, 232), 930, 7)
    draw.text((58, H - 50), source, font=font(17), fill=(210, 210, 205))
    draw.text((W - 58, H - 50), "내부 검토 · 게시 불가", font=font(17, True), fill=(210, 210, 205), anchor="ra")
    return image


def map_card(index: int, total: int) -> Image.Image:
    bg = cover_crop(ASSETS / "account_a" / "la_linea_2024.jpg")
    bg = bg.filter(ImageFilter.GaussianBlur(7))
    bg = ImageEnhance.Brightness(bg).enhance(0.46)
    draw = ImageDraw.Draw(bg)
    draw.text((58, 46), f"ACCOUNT A  ·  {TODAY}", font=font(22, True), fill="white")
    draw.text((W - 58, 46), f"{index:02d}/{total:02d}", font=font(22, True), fill="white", anchor="ra")
    draw.text((70, 225), "SPAIN", font=font(30, True), fill="#B5C5D8")
    draw.text((70, 285), "LA LÍNEA", font=font(64, True), fill="white")
    draw.line((180, 500, 820, 790), fill="#FFCA52", width=10)
    draw.ellipse((155, 475, 205, 525), fill="#FFCA52")
    draw.ellipse((795, 765, 845, 815), fill="#FFCA52")
    draw.text((700, 845), "GIBRALTAR", font=font(47, True), fill="white")
    draw.text((700, 910), "영국령", font=font(26), fill="#D6DDE7")
    draw_multiline(draw, (70, 1030), "영국령인데,\n육지는 스페인과 붙어 있다", font(58, True), "white", 920, 6)
    draw.text((58, H - 50), "지도 설명용 자체 그래픽 · 배경 CC0", font=font(17), fill=(210, 210, 205))
    draw.text((W - 58, H - 50), "내부 검토 · 게시 불가", font=font(17, True), fill=(210, 210, 205), anchor="ra")
    return bg


def quote_card(path: Path, account: str, index: int, total: int, quote: str, subline: str,
               source: str, accent: str, label: str) -> Image.Image:
    image = instagram_media_crop(path).filter(ImageFilter.GaussianBlur(16))
    image = ImageEnhance.Brightness(image).enhance(0.42)
    draw = ImageDraw.Draw(image)
    draw.text((58, 46), f"ACCOUNT {account}  ·  {TODAY}", font=font(22, True), fill="white")
    draw.text((W - 58, 46), f"{index:02d}/{total:02d}", font=font(22, True), fill="white", anchor="ra")
    box = draw.textbbox((0, 0), label, font=font(21, True))
    box_w = box[2] - box[0] + 42
    draw.rounded_rectangle((58, 330, 58 + box_w, 380), 25, fill=accent)
    draw.text((79, 355), label, font=font(21, True), fill="white", anchor="lm")
    y = draw_multiline(draw, (58, 475), quote, font(76, True), "white", 950, 16)
    draw_multiline(draw, (60, y + 34), subline, font(29), (226, 226, 222), 920, 8)
    draw.text((58, H - 50), source, font=font(17), fill=(210, 210, 205))
    draw.text((W - 58, H - 50), "내부 검토 · 게시 불가", font=font(17, True), fill=(210, 210, 205), anchor="ra")
    return image


def salon_cover(before_path: Path, after_path: Path, index: int, total: int) -> Image.Image:
    before = ImageOps.exif_transpose(Image.open(before_path)).convert("RGB").crop((0, 520, 1440, 2050))
    after = ImageOps.exif_transpose(Image.open(after_path)).convert("RGB").crop((0, 560, 1440, 1860))
    before = cover_crop_from_image(before, (W // 2, H))
    after = cover_crop_from_image(after, (W // 2, H))
    image = Image.new("RGB", (W, H), "black")
    image.paste(before, (0, 0))
    image.paste(after, (W // 2, 0))
    image = darken_bottom(image, start=0.44, max_alpha=242)
    draw = ImageDraw.Draw(image)
    draw.text((58, 46), f"ACCOUNT B  ·  {TODAY}", font=font(22, True), fill="white")
    draw.text((W - 58, 46), f"{index:02d}/{total:02d}", font=font(22, True), fill="white", anchor="ra")
    draw.rounded_rectangle((58, 790, 265, 840), 25, fill="#FF3B30")
    draw.text((80, 815), "THE SHOCK", font=font(21, True), fill="white", anchor="lm")
    y = draw_multiline(draw, (58, 880), "17만 원 냈는데,\n바리깡으로 한 번에?", font(67, True), "white", 950, 9)
    draw_multiline(draw, (60, y + 18), "시술 전 → 제보된 결과", font(28), (236, 236, 232), 920, 7)
    draw.text((58, H - 50), "원자료: owner inbox 공개 게시물 캡처 · 사실 재검증 필요", font=font(17), fill=(210, 210, 205))
    draw.text((W - 58, H - 50), "내부 검토 · 게시 불가", font=font(17, True), fill=(210, 210, 205), anchor="ra")
    return image


def save_pack(slug: str, account: str, category: str, topic: str, slides: list[Image.Image],
              plan_slides: list[dict], sources: list[dict], manifest_extra: dict) -> None:
    folder = ROOT / slug
    folder.mkdir(parents=True, exist_ok=True)
    for index, slide in enumerate(slides, 1):
        slide.save(folder / f"slide_{index:02d}.png", optimize=True)
    plan = {
        "schema_version": "image_first_owner_review_v2",
        "generated_by": "Codex CTO integration lane",
        "generated_at": "2026-07-17",
        "account": account,
        "category": category,
        "topic": topic,
        "slide_count": len(slides),
        "review_only": True,
        "publishing_ready": False,
        "slides": plan_slides,
        "sources": sources,
    }
    (folder / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "schema_version": "image_first_review_manifest_v2",
        "generated_by": "Codex CTO integration lane",
        "review_only": True,
        "publishing_ready": False,
        "rights_status": "restricted_internal_editorial_review",
        "source_recheck_required": True,
        "actual_publish_requires_explicit_owner_approval": True,
        **manifest_extra,
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    contact_sheet(folder, len(slides))


def contact_sheet(folder: Path, total: int) -> None:
    tw, th, cols = 270, 338, 4
    rows = math.ceil(total / cols)
    sheet = Image.new("RGB", (tw * cols, th * rows), "#14171C")
    for index in range(1, total + 1):
        image = Image.open(folder / f"slide_{index:02d}.png").convert("RGB")
        image.thumbnail((tw, th), Image.Resampling.LANCZOS)
        x = ((index - 1) % cols) * tw
        y = ((index - 1) // cols) * th
        sheet.paste(image, (x, y))
    sheet.save(folder / "contact_sheet.png", optimize=True)


def build_account_a() -> None:
    a = ASSETS / "account_a"
    total = 7
    spec = [
        ("gibraltar_current_01.jpg", "117년 된 장벽,\n0시에 열렸다", "지브롤터-스페인 육로 검문 철거", "BREAKING", 0.50),
        ("MAP", "", "", "", 0.50),
        ("gibraltar_current_02.jpg", "장벽을 걷어낸 밤", "브렉시트 이후 협상 4년 만에", "THE NIGHT", 0.48),
        ("gibraltar_video_frame.jpg", "여권을 보여주던\n육로 검문이 멈췄다", "7월 15일, 사람과 차량의 자유 통행 시작", "FIRST CROSSING", 0.48),
        ("la_linea_2024.jpg", "매일 약 1만 5천 명", "스페인에서 지브롤터로 출근하던 사람들", "THE PEOPLE", 0.45),
        ("gibraltar_airport.jpg", "장벽은 열렸지만", "외부 입국 심사는 공항·항만으로 이동", "WHAT CHANGED", 0.43),
        ("gibraltar_current_01.jpg", "주권은 그대로", "사라진 건 육로의 상시 검문과 통행 장벽", "THE LINE", 0.50),
    ]
    slides: list[Image.Image] = []
    plan_slides: list[dict] = []
    for i, (asset, headline, subline, label, focus) in enumerate(spec, 1):
        if asset == "MAP":
            image = map_card(i, total)
            media_type = "editorial"
            asset_name = "self-authored map over CC0 background"
            headline = "영국령인데, 육지는 스페인과 붙어 있다"
        else:
            image = card(a / asset, "A", i, total, headline, subline, "UK·EU·Gibraltar 공식 / AP 교차확인", "#F2A900", label=label, focus_y=focus, headline_size=66)
            media_type = "image"
            asset_name = asset
        slides.append(image)
        plan_slides.append({"slide": i, "role": label.lower().replace(" ", "_") or "map", "media_type": media_type, "headline": headline, "asset": asset_name, "copy_density": "minimal"})
    sources = [
        {"publisher": "UK Government", "url": "https://www.gov.uk/government/news/uk-finalises-historic-treaty-with-eu-to-secure-economic-future-of-gibraltar", "role": "primary facts"},
        {"publisher": "Government of Gibraltar", "url": "https://www.gibraltar.gov.gi/press-releases/another-historic-day-for-gibraltar-as-checks-removed-from-frontier-5612026-12204", "role": "primary event confirmation"},
        {"publisher": "AP", "url": "https://apnews.com/article/spain-gibraltar-uk-brexit-9113dd58dc8220826038022e84e3b662", "role": "independent report and licensed imagery"},
    ]
    save_pack("account_a_gibraltar", "A", "world_news", "117년 된 지브롤터 육로 장벽이 열린 날", slides, plan_slides, sources,
              {"asset_warning": "AP/JW imagery is license-required and used only for internal concept review; Wikimedia assets retain file-level licenses", "claim_boundary": "land-frontier routine checks and physical barrier removal; sovereignty remains unresolved"})


def build_account_b() -> None:
    b = ASSETS / "account_b"
    total = 7
    # Source carousel is stored in reverse order: file 18 is original slide 1.
    spec = [
        ("COVER", "17만 원 냈는데,\n바리깡으로 한 번에?", "시술 전 → 제보된 결과", "THE SHOCK"),
        ("salon_17.jpg", "원한 건 새치 염색", "시술 전 모습", "BEFORE"),
        ("QUOTE", "“투블럭이\n어울릴 것 같아요”", "새치 염색 상담 중 나온 스타일 변경 제안", "THE TURN"),
        ("salon_15.jpg", "알겠다고 하자,\n뒤통수를 확 밀었다", "제보자가 설명한 순간", "THE CUT"),
        ("salon_14.jpg", "거울을 보고\n말을 잃었다", "현장 반응", "THE RESULT"),
        ("salon_13.jpg", "결국 17만 원을 결제", "귀가 후 다시 항의", "THE PAYMENT"),
        ("salon_12.jpg", "“실수가 아니다”", "사과보다 작품·콘셉트를 강조했다는 제보", "THE REPLY"),
    ]
    slides: list[Image.Image] = []
    plan_slides: list[dict] = []
    for i, (asset, headline, subline, label) in enumerate(spec, 1):
        if asset == "COVER":
            image = salon_cover(b / "salon_17.jpg", b / "salon_14.jpg", i, total)
            asset_name = "salon_17.jpg + salon_14.jpg evidence crop"
            media_type = "comparison"
        elif asset == "QUOTE":
            image = quote_card(b / "salon_17.jpg", "B", i, total, headline, subline, "원자료: owner inbox 공개 게시물 캡처 · 사실 재검증 필요", "#FF3B30", label)
            asset_name = "salon_17.jpg blurred editorial background"
            media_type = "editorial"
        else:
            image = card(b / asset, "B", i, total, headline, subline, "원자료: owner inbox 내 공개 게시물 캡처 · 사실 재검증 필요", "#FF3B30", screenshot=True, label=label, headline_size=61, start=0.52)
            asset_name = asset
            media_type = "screenshot"
        slides.append(image)
        plan_slides.append({"slide": i, "role": label.lower().replace(" ", "_"), "media_type": media_type, "headline": headline, "asset": asset_name, "copy_density": "minimal", "is_factual_evidence": "source-capture only; claim unverified"})
    sources = [{"publisher": "owner_analysis_inbox public-post capture", "url": None, "role": "raw owner-provided reference; not approved fact"}]
    save_pack("account_b_salon", "B", "issue_real_story", "17만 원 미용실 바리깡 피해 제보", slides, plan_slides, sources,
              {"asset_warning": "public-post screenshots and broadcaster imagery require permission/quotation review; identities remain obscured", "fact_status": "unverified owner-provided raw material", "comments_used": False})


def build_dior() -> None:
    d = ASSETS / "account_c_dior"
    total = 7
    spec = [
        ("runway_13.png", "DIOR MEN", "2027 S/S", "SEASON PREVIEW"),
        ("runway_01.png", "친숙함을\n다시 조립하다", "이번 시즌의 짧은 문장", "THE IDEA"),
        ("runway_18.png", "커진 턱시도", "몸과 옷 사이의 거리", "SILHOUETTE"),
        ("runway_14.png", "프린트된\n하운즈투스", "익숙한 패턴을 다른 방식으로", "MATERIAL"),
        ("runway_10.png", "정교함 위\n거친 표면", "한 장면에 겹친 두 감각", "TEXTURE"),
        ("runway_20.png", "낮은 색,\n큰 질감", "사진이 먼저 보이게", "PALETTE"),
        ("runway_23.png", "27 S/S를\n미리 본 장면", "설명은 여기까지만", "THE LOOK"),
    ]
    slides: list[Image.Image] = []
    plan_slides: list[dict] = []
    for i, (asset, headline, subline, label) in enumerate(spec, 1):
        image = card(d / asset, "C", i, total, headline, subline, "DIOR MEN 2027 S/S · FashionN 보도 이미지", "#C62828", label=label, focus_y=0.42, headline_size=68, start=0.54)
        slides.append(image)
        plan_slides.append({"slide": i, "role": label.lower().replace(" ", "_"), "media_type": "image", "headline": headline, "asset": asset, "copy_density": "minimal"})
    sources = [{"publisher": "DIOR", "url": "https://www.dior.com/ko_kr/fashion/mens-fashion/shows/summer-2027-show", "role": "official season reference"}]
    save_pack("account_c_dior", "C", "fashion", "DIOR MEN 2027 S/S · 이미지 중심 축약본", slides, plan_slides, sources,
              {"asset_warning": "real runway imagery; internal editorial review only; publication rights must be cleared", "owner_correction_applied": "actual Dior imagery dominates; season explanation is intentionally short"})


def build_valentino() -> None:
    v = ASSETS / "account_c_valentino"
    total = 8
    spec = [
        ("01_duo_model.jpg", "6년 만의 새 향수", "VENDETTA", "NEW · 07.13"),
        ("02_duo_pack.jpg", "DONNA × UOMO", "같은 열기, 다른 향", "THE DUO"),
        ("03_donna.jpg", "DONNA", "튜베로즈 · 레드 오렌지", "HER SCENT"),
        ("04_tuberose.jpg", "밝게 피고,\n깊게 남는다", "튜베로즈", "THE FLOWER"),
        ("06_uomo.jpg", "UOMO", "진저 · 시나몬 리큐어", "HIS SCENT"),
        ("07_ginger.jpg", "차갑게 시작해,\n뜨겁게 번진다", "진저", "THE HEAT"),
        ("05_orange.jpg", "한 번 더\n시선을 잡는 색", "레드 오렌지", "THE FLASH"),
        ("02_duo_pack.jpg", "첫 비주얼은 여기까지", "캠페인 필름은 올여름 이어진다", "TO BE CONTINUED"),
    ]
    slides: list[Image.Image] = []
    plan_slides: list[dict] = []
    for i, (asset, headline, subline, label) in enumerate(spec, 1):
        image = card(v / asset, "C", i, total, headline, subline, "Valentino Beauty 공식 이미지 · Inez & Vinoodh", "#D50032", label=label, focus_y=0.48, headline_size=68, start=0.56)
        slides.append(image)
        plan_slides.append({"slide": i, "role": label.lower().replace(" ", "_"), "media_type": "image", "headline": headline, "asset": asset, "copy_density": "minimal", "motion_reuse": "push-in/glint/quick-cut candidate"})
    sources = [
        {"publisher": "Valentino Beauty", "url": "https://www.valentino-beauty.com/int/fragrances/women-fragrances/vendetta/vendetta-donna/MPL02097.html", "role": "official product facts and images"},
        {"publisher": "PR Newswire", "url": "https://www.prnewswire.com/news-releases/valentino-beauty-unveils-vendetta-the-scents-of-unstoppable-passion-302823371.html", "role": "2026-07-13 launch confirmation"},
    ]
    save_pack("account_c_valentino", "C", "beauty", "Valentino Beauty VENDETTA · 2026-07-13 공개", slides, plan_slides, sources,
              {"asset_warning": "official brand/PDP assets are restricted editorial review material; social publication rights are not implied", "motion_sources_available": True, "ai_generated_product_substitute": False})


def build_index() -> None:
    packs = [
        ("account_a_gibraltar", "A", "오늘 세계뉴스", "117년 된 육로 장벽이 열린 날", "7장 · 실제 장면/지도/사람"),
        ("account_b_salon", "B", "오늘 이슈·실화", "17만 원 미용실 바리깡 피해", "7장 · 실제 제보 화면 중심"),
        ("account_c_dior", "C", "패션 교정본", "DIOR MEN 2027 S/S", "7장 · 실제 룩 + 최소 설명"),
        ("account_c_valentino", "C", "오늘 뷰티", "Valentino VENDETTA", "8장 · 공식 4:5 이미지"),
    ]
    cards = []
    for slug, account, kicker, title, meta in packs:
        cards.append(f'''<article class="a{account.lower()}">
          <a href="{slug}/contact_sheet.png"><img src="{slug}/contact_sheet.png" loading="lazy" alt="{html.escape(title)} contact sheet"></a>
          <div class="copy"><span>{html.escape(kicker)}</span><h2>{html.escape(title)}</h2><p>{html.escape(meta)}</p>
          <div><a class="primary" href="{slug}/slide_01.png">첫 장 보기</a><a href="{slug}/plan.json">plan</a><a href="{slug}/manifest.json">manifest</a></div></div></article>''')
    page = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>2026-07-17 이미지 중심 CardNews v2</title><style>
:root{{color-scheme:dark;--bg:#090b0f;--panel:#151922;--muted:#a6afbd;--line:#2b313c}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:#fff;font-family:"Malgun Gothic",sans-serif}}header{{padding:72px 5vw 42px;background:radial-gradient(circle at 12% 0,#263b68 0,transparent 42%);border-bottom:1px solid var(--line)}}h1{{font-size:clamp(38px,5vw,68px);letter-spacing:-3px;margin:0 0 14px}}header p{{max-width:900px;line-height:1.7;color:var(--muted);font-size:18px}}.badge{{display:inline-block;margin-top:10px;padding:10px 16px;border-radius:999px;background:#4b2525;color:#ffc2c2;font-weight:800}}main{{padding:42px 5vw 70px;display:grid;grid-template-columns:repeat(auto-fit,minmax(390px,1fr));gap:28px}}article{{background:var(--panel);border:1px solid var(--line);border-radius:22px;overflow:hidden;box-shadow:0 24px 65px #0009}}article img{{display:block;width:100%;background:#111}}.copy{{padding:24px}}.copy span{{font-weight:900;color:#8cc7ff}}h2{{font-size:28px;margin:8px 0}}.copy p{{color:var(--muted);margin-bottom:20px}}.copy a{{display:inline-block;color:#fff;text-decoration:none;margin:0 10px 8px 0;font-weight:800}}.copy .primary{{background:#377dff;border-radius:999px;padding:11px 16px}}.ab{{border-top:5px solid #ff4c42}}.ac{{border-top:5px solid #dc4d8d}}footer{{padding:35px 5vw 60px;border-top:1px solid var(--line);color:var(--muted);line-height:1.7}}</style></head>
<body><header><h1>IMAGE-FIRST / v2</h1><p>텍스트 박스를 줄이고 실제 이미지·장면·제품이 내용을 전달하도록 다시 제작한 2026년 7월 17일 내부 검토본입니다. 고정 4장이 아닌 주제별 가변 구성입니다.</p><span class="badge">내부 검토 전용 · 권리/팩트 재검증 전 게시 불가</span></header><main>{''.join(cards)}</main><footer>총 4개 콘셉트 · 29장 · 1080×1350. 기존 76장 갤러리는 변경하지 않았습니다. 실제 게시·업로드·자동화는 수행하지 않았습니다.</footer></body></html>'''
    (ROOT / "index.html").write_text(page, encoding="utf-8")
    guide = """# Image-first CardNews v2 Review\n\n- Date: 2026-07-17\n- Scope: 4 concepts, 29 slides, 1080x1350\n- Purpose: owner-only local review of the corrected image-first direction\n- Publishing: blocked\n- Rights/fact status: recheck every source and asset before any external use\n- Existing 76-slide gallery: preserved unchanged\n\nReview the contact sheet first, then open individual slides only when needed.\n"""
    (ROOT / "REVIEW_GUIDE.md").write_text(guide, encoding="utf-8")


if __name__ == "__main__":
    build_account_a()
    build_account_b()
    build_dior()
    build_valentino()
    build_index()
    print(json.dumps({"status": "ok", "gallery": str(ROOT / "index.html"), "packs": 4, "slides": 29}, ensure_ascii=False))
