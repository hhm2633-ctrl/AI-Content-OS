from __future__ import annotations

import html
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
W, H = 1080, 1350
FONT = Path(r"C:\Windows\Fonts\NotoSansKR-VF.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\malgunbd.ttf")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT), size=size)


def wrap(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        current = ""
        for ch in paragraph:
            trial = current + ch
            if draw.textbbox((0, 0), trial, font=f)[2] <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = ch
        lines.append(current)
    return lines


def text_block(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, f: ImageFont.FreeTypeFont,
               fill: str, max_width: int, spacing: int = 12, anchor: str = "la") -> int:
    x, y = xy
    lines = wrap(draw, text, f, max_width)
    line_h = f.size + spacing
    for line in lines:
        draw.text((x, y), line, font=f, fill=fill, anchor=anchor)
        y += line_h
    return y


def cover_crop(path: Path, size: tuple[int, int] = (W, H)) -> Image.Image:
    im = Image.open(path).convert("RGB")
    scale = max(size[0] / im.width, size[1] / im.height)
    new = im.resize((round(im.width * scale), round(im.height * scale)), Image.Resampling.LANCZOS)
    left = max(0, (new.width - size[0]) // 2)
    top = max(0, (new.height - size[1]) // 2)
    return new.crop((left, top, left + size[0], top + size[1]))


def gradient_overlay(im: Image.Image, top_alpha: int, bottom_alpha: int, color=(0, 0, 0)) -> Image.Image:
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    px = layer.load()
    for y in range(im.height):
        a = round(top_alpha + (bottom_alpha - top_alpha) * (y / max(1, im.height - 1)))
        for x in range(im.width):
            px[x, y] = (*color, a)
    return Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")


def pill(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fill: str, fg: str,
         f: ImageFont.FreeTypeFont | None = None, pad_x=22, pad_y=10) -> None:
    f = f or font(30, True)
    box = draw.textbbox((0, 0), text, font=f)
    w, h = box[2] - box[0], box[3] - box[1]
    x, y = xy
    draw.rounded_rectangle((x, y, x + w + pad_x * 2, y + h + pad_y * 2), radius=24, fill=fill)
    draw.text((x + pad_x, y + pad_y - 2), text, font=f, fill=fg)


def footer(draw: ImageDraw.ImageDraw, idx: int, total: int, source: str, color: str, fg: str) -> None:
    draw.line((72, 1265, 1008, 1265), fill=color, width=2)
    draw.text((72, 1286), source, font=font(22), fill=fg)
    draw.text((1008, 1286), f"{idx:02d}/{total:02d}", font=font(23, True), fill=fg, anchor="ra")


def save(im: Image.Image, folder: Path, idx: int) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    im.save(folder / f"slide_{idx:02d}.png", quality=95)


def news_slide(idx: int, total: int, kind: str, headline: str, body: str = "", note: str = "") -> Image.Image:
    navy, red, paper, ink, muted = "#14213D", "#E63946", "#F7F4EC", "#111827", "#526071"
    if kind == "cover":
        im = cover_crop(ROOT / "assets" / "legal.jpg")
        im = gradient_overlay(im, 35, 235, (10, 18, 38))
        d = ImageDraw.Draw(im)
        pill(d, (72, 72), "ACCOUNT A · NEWS EXPLAINER", red, "white", font(25, True))
        d.text((72, 725), "오늘의 뉴스,\n한 문장보다 한 단계 더", font=font(32, True), fill="#E7ECF7", spacing=6)
        text_block(d, (72, 875), headline, font(77, True), "white", 900, spacing=11)
        d.text((72, 1192), note, font=font(26), fill="#D8DEEA")
        footer(d, idx, total, "이데일리 · News1 보도 교차 확인", red, "#D8DEEA")
        return im

    im = Image.new("RGB", (W, H), paper)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 26, H), fill=red)
    d.text((72, 70), "THE CONTEXT", font=font(25, True), fill=red)
    d.text((1008, 70), "NEWS / LAW", font=font(25, True), fill=navy, anchor="ra")
    if kind == "quote":
        d.text((72, 220), "“", font=font(180, True), fill="#D7DCE5")
        text_block(d, (120, 330), headline, font(68, True), ink, 830, spacing=16)
        d.rounded_rectangle((120, 715, 960, 940), radius=24, fill="white", outline="#D8DDE5", width=2)
        text_block(d, (165, 770), body, font(34), muted, 750, spacing=14)
    elif kind == "three":
        text_block(d, (72, 190), headline, font(61, True), ink, 900, spacing=14)
        items = body.split("|")
        colors = [red, "#F0A202", navy]
        y = 440
        for n, item in enumerate(items, 1):
            d.ellipse((72, y, 140, y + 68), fill=colors[n - 1])
            d.text((106, y + 33), str(n), font=font(30, True), fill="white", anchor="mm")
            text_block(d, (168, y - 3), item, font(37, True), ink, 790, spacing=10)
            y += 215
    elif kind == "split":
        text_block(d, (72, 190), headline, font(61, True), ink, 900, spacing=14)
        left, right = body.split("|")
        d.rounded_rectangle((72, 500, 512, 1040), radius=32, fill=navy)
        d.rounded_rectangle((568, 500, 1008, 1040), radius=32, fill="white", outline="#CFD5DF", width=3)
        text_block(d, (112, 565), left, font(42, True), "white", 360, spacing=14)
        text_block(d, (608, 565), right, font(42, True), ink, 360, spacing=14)
    else:
        text_block(d, (72, 190), headline, font(61, True), ink, 900, spacing=14)
        d.rounded_rectangle((72, 475, 1008, 1025), radius=34, fill="white", outline="#D8DDE5", width=2)
        text_block(d, (122, 550), body, font(39), ink, 835, spacing=18)
        if note:
            d.text((122, 950), note, font=font(25), fill=muted)
    footer(d, idx, total, "보도 사실과 법률 절차를 분리해 읽기", red, muted)
    return im


def incident_slide(idx: int, total: int, kind: str, headline: str, body: str = "", tag: str = "") -> Image.Image:
    bg, teal, cyan, orange, white, gray = "#061A1F", "#0B353B", "#25E4D3", "#FF8A5B", "#F4FFFD", "#A8C0C3"
    if kind == "cover":
        im = cover_crop(ROOT / "assets" / "ai_fake_chat.jpg")
        im = gradient_overlay(im, 65, 245, (1, 18, 23))
        d = ImageDraw.Draw(im)
        pill(d, (68, 68), "INCIDENT · DIGITAL EVIDENCE", cyan, bg, font(24, True))
        d.text((68, 780), "가짜 대화가\n진짜 수사기록이 됐다", font=font(39, True), fill=cyan, spacing=6)
        text_block(d, (68, 940), headline, font(72, True), white, 910, spacing=12)
        footer(d, idx, total, "머니투데이(뉴시스 인용) · 2026.07.16", cyan, gray)
        return im
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 165), fill=teal)
    d.text((68, 50), f"TRACE {idx - 1:02d}", font=font(30, True), fill=cyan)
    d.text((1012, 54), tag, font=font(25, True), fill=gray, anchor="ra")
    if kind == "timeline":
        text_block(d, (68, 230), headline, font(62, True), white, 910, spacing=14)
        d.line((125, 525, 125, 1050), fill=cyan, width=8)
        for n, part in enumerate(body.split("|")):
            y = 545 + n * 170
            d.ellipse((96, y, 154, y + 58), fill=cyan)
            d.text((125, y + 29), str(n + 1), font=font(24, True), fill=bg, anchor="mm")
            text_block(d, (190, y - 5), part, font(37, True), white, 770, spacing=12)
    elif kind == "evidence":
        text_block(d, (68, 230), headline, font(61, True), white, 910, spacing=14)
        d.rounded_rectangle((68, 520, 1012, 1000), radius=28, fill=teal, outline="#18606A", width=3)
        d.text((115, 570), "확인된 기사 서술", font=font(28, True), fill=cyan)
        text_block(d, (115, 650), body, font(39), white, 850, spacing=18)
        d.text((115, 940), "※ 실제 카카오톡 화면은 확보되지 않아 재현하지 않음", font=font(25), fill=orange)
    elif kind == "impact":
        text_block(d, (68, 230), headline, font(62, True), white, 910, spacing=14)
        d.rounded_rectangle((68, 540, 1012, 1005), radius=32, fill=orange)
        text_block(d, (116, 620), body, font(49, True), bg, 850, spacing=18)
    elif kind == "check":
        text_block(d, (68, 230), headline, font(61, True), white, 910, spacing=14)
        y = 515
        for part in body.split("|"):
            d.rounded_rectangle((68, y, 1012, y + 130), radius=22, fill=teal)
            d.text((105, y + 66), "✓", font=font(40, True), fill=cyan, anchor="lm")
            d.text((172, y + 66), part, font=font(34, True), fill=white, anchor="lm")
            y += 155
    else:
        text_block(d, (68, 230), headline, font(62, True), white, 910, spacing=14)
        text_block(d, (68, 555), body, font(43), white, 910, spacing=20)
    footer(d, idx, total, "원문 미확보 댓글·대화 캡처는 사용하지 않음", cyan, gray)
    return im


def economy_slide(idx: int, total: int, kind: str, headline: str, body: str = "", label: str = "") -> Image.Image:
    black, lime, blue, white, gray = "#0D1117", "#B9FF44", "#4C77FF", "#F8FAFC", "#9AA6B2"
    if kind == "cover":
        im = cover_crop(ROOT / "assets" / "leverage_yna.jpg")
        im = gradient_overlay(im, 15, 242, (3, 8, 15))
        d = ImageDraw.Draw(im)
        pill(d, (68, 68), "MARKET RULE CHANGE", lime, black, font(25, True))
        d.text((68, 690), "단일종목 레버리지 ETF", font=font(33, True), fill="#DCE5F3")
        text_block(d, (68, 770), headline, font(81, True), white, 900, spacing=12)
        d.rounded_rectangle((68, 1110, 710, 1195), radius=20, fill=lime)
        d.text((100, 1152), "현금 3천만 원 · 20주 단위", font=font(32, True), fill=black, anchor="lm")
        footer(d, idx, total, "연합뉴스 · 이데일리 교차 확인", lime, "#DCE5F3")
        return im
    im = Image.new("RGB", (W, H), black)
    d = ImageDraw.Draw(im)
    d.text((68, 62), "MONEY / MARKET", font=font(26, True), fill=lime)
    d.text((1012, 62), label, font=font(24, True), fill=gray, anchor="ra")
    if kind == "number":
        text_block(d, (68, 185), headline, font(58, True), white, 910, spacing=14)
        d.text((540, 600), body, font=font(180, True), fill=lime, anchor="mm")
        d.text((540, 810), "기본예탁금 · 현금", font=font(38, True), fill=white, anchor="mm")
    elif kind == "versus":
        text_block(d, (68, 185), headline, font(58, True), white, 910, spacing=14)
        left, right = body.split("|")
        d.rounded_rectangle((68, 485, 510, 1000), radius=32, fill="#18212B")
        d.rounded_rectangle((570, 485, 1012, 1000), radius=32, fill=blue)
        text_block(d, (112, 560), left, font(43, True), white, 350, spacing=16)
        text_block(d, (614, 560), right, font(43, True), white, 350, spacing=16)
    elif kind == "chart":
        text_block(d, (68, 185), headline, font(58, True), white, 910, spacing=14)
        parts = body.split("|")
        y = 510
        for n, part in enumerate(parts):
            width = [760, 620, 490][n]
            d.rounded_rectangle((68, y, 68 + width, y + 92), radius=18, fill=[lime, blue, "#627083"][n])
            d.text((96, y + 46), part, font=font(31, True), fill=black if n == 0 else white, anchor="lm")
            y += 150
    elif kind == "check":
        text_block(d, (68, 185), headline, font(58, True), white, 910, spacing=14)
        y = 500
        for part in body.split("|"):
            d.rounded_rectangle((68, y, 1012, y + 128), radius=20, outline="#34414F", width=3)
            d.ellipse((102, y + 36, 158, y + 92), fill=lime)
            d.text((130, y + 63), "!", font=font(30, True), fill=black, anchor="mm")
            d.text((190, y + 64), part, font=font(32, True), fill=white, anchor="lm")
            y += 155
    else:
        text_block(d, (68, 185), headline, font(58, True), white, 910, spacing=14)
        text_block(d, (68, 530), body, font(43), white, 910, spacing=20)
    footer(d, idx, total, "제도 시행 세부 일정은 금융사 공지 재확인 필요", lime, gray)
    return im


PACKS: dict[str, dict[str, Any]] = {
    "news_legal_explainer": {
        "category": "major_news_policy",
        "topic": "심우정 전 검찰총장 구속영장 기각과 영장 기각의 의미",
        "sources": [
            {"publisher": "이데일리", "url": "https://www.edaily.co.kr/News/Read?newsId=06546886645515176&mediaCodeNo=257"},
            {"publisher": "News1", "url": "https://www.news1.kr/society/court-prosecution/6231083"},
            {"publisher": "머니투데이", "url": "https://www.mt.co.kr/society/2026/07/16/2026071616531328287"},
        ],
        "slides": [
            ("cover", "구속영장 기각.\n그게 ‘혐의 없음’은 아니다", "", "2026.07.16 밤, 법원이 영장을 기각했다"),
            ("quote", "법원이 판단한 건\n‘지금 구속할 필요’", "공개 보도상 기각 사유는 도주·증거인멸 우려가 낮다는 판단이었다.", ""),
            ("split", "영장심사와 본안판단은 다르다", "구속영장\n신병 확보 필요성\n도주·증거인멸 우려|본안 재판\n혐의 입증 여부\n최종 유·무죄", ""),
            ("three", "기사에서 이 세 단어를\n섞어 읽지 말 것", "구속: 수사·재판 중 신병 확보|기소: 재판에 넘기는 결정|유죄: 법원의 본안 판단", ""),
            ("body", "영장이 기각돼도\n수사나 재판은 끝난 게 아니다", "기각은 구속 필요성에 대한 판단이다.\n혐의 자체에 대한 최종 결론은 이후 절차에서 다뤄질 수 있다.", "법률 절차 일반 설명"),
            ("body", "이 사건에서 지금\n확정적으로 말할 수 있는 것", "법원은 심우정 전 검찰총장 등에 대한 구속영장을 기각했다.\n보도된 기각 사유는 도주·증거인멸 우려가 낮다는 취지다.", "그 밖의 혐의 판단은 단정하지 않음"),
            ("body", "뉴스 한 줄을 볼 때\n마지막으로 확인할 것", "① 법원이 실제로 판단한 범위\n② 기사 제목이 ‘구속’과 ‘유죄’를 섞지 않았는지\n③ 후속 수사·재판이 남았는지", "내부 검토용 · 게시 전 원문 재검증"),
        ],
    },
    "incident_ai_fake_chat": {
        "category": "incident_conflict",
        "topic": "AI로 조작한 카카오톡 대화와 현금인출증을 수사기관에 제출한 사건",
        "sources": [
            {"publisher": "머니투데이(뉴시스 인용)", "url": "https://www.mt.co.kr/society/2026/07/16/2026071620130254093"}
        ],
        "slides": [
            ("cover", "AI로 만든 가짜 카톡.\n진짜 피해자가 무고범이 됐다", "", ""),
            ("timeline", "시작은 타인의 이름으로\n받은 1,900만 원 대출", "2024년 1월·8월, 타인 인적사항 도용|피해자 명의로 대출 신청한 것처럼 꾸밈|검찰은 1,900만 원 대출 혐의를 적시", "사건 흐름"),
            ("body", "피해자가 고소하자\n증거가 ‘새로’ 생겼다", "보도에 따르면 피고인은 피해자에게 현금 1,900만 원을 빌려줬다가 돌려받았다는 취지의 자료를 만들었다.", "전환점"),
            ("evidence", "그 자료는 AI로 조작한\n카카오톡 대화와 현금인출증", "검찰 조사 내용으로 보도된 사실이며, 실제 대화 원본이나 캡처는 공개 자료에서 확보하지 못했다.", "조작 자료"),
            ("body", "조작 자료가 들어간 곳은\nSNS가 아니라 수사기관", "경찰에 제출됐고, 법정에서는 허위 증언까지 한 혐의가 더해졌다고 보도됐다.", "수사·재판"),
            ("impact", "결국 뒤집힌 사람", "사기 피해를 신고한 B씨가\n한때 무고 혐의로 재판에 넘겨졌다고 보도됐다.", "피해"),
            ("body", "검찰이 적용한 혐의", "위계공무집행방해·위증 등.\n대구지검은 26세 A씨를 구속기소했다고 밝혔다.", "현재 단계"),
            ("check", "AI 시대에 ‘캡처 한 장’만\n믿으면 안 되는 이유", "원본 기기·계정 기록 확인|금융 거래 원본과 시간대 대조|제출 경로와 파일 생성 이력 확인", "검증 포인트"),
            ("body", "이 사건의 핵심은\nAI가 아니라 검증 절차다", "그럴듯한 화면은 만들 수 있다.\n하지만 진짜 기록은 원본·시간·거래·제출 경로가 함께 맞아야 한다.", "마무리"),
        ],
    },
    "economy_leverage_etf": {
        "category": "economy_market",
        "topic": "단일종목 레버리지 ETF 기본예탁금 3천만 원과 20주 단위 거래",
        "sources": [
            {"publisher": "이데일리", "url": "https://www.edaily.co.kr/News/Read?newsId=05516966645515176&mediaCodeNo=257"},
            {"publisher": "연합뉴스", "url": "https://www.yna.co.kr/view/AKR20260716165353002?section=economy/all"},
        ],
        "slides": [
            ("cover", "이제 1주씩 못 산다?\n3천만 원 문턱 생긴다", "", ""),
            ("number", "가장 먼저 바뀌는 숫자", "3,000만 원", "진입 조건"),
            ("versus", "주문 단위도 달라진다", "기존\n1주 단위로\n매매 가능|변경\n20주 단위로\n사고팔기", "거래 단위"),
            ("chart", "당국이 함께 내놓은\n세 가지 제동", "신규 상장 잠정 중단|상품 광고 금지|기본예탁금·매매단위 강화", "보완책"),
            ("body", "해외 상장 상품이면\n피할 수 있을까?", "연합뉴스 보도에 따르면 국내 주식을 기초로 한 상품은 해외 상장 상품도 적용 대상에 포함된다.", "적용 범위"),
            ("body", "왜 이렇게까지 막나", "단일종목 레버리지 상품이 삼성전자·SK하이닉스 등 현물 주가의 변동성을 키울 수 있다는 지적이 배경이다.", "정책 배경"),
            ("check", "보유자·매수 예정자가\n지금 확인할 것", "내 증권사의 시행 일정|예탁금 인정 방식과 주문 단위|보유 상품의 국내주식 기초 여부", "체크리스트"),
            ("body", "한 줄 결론", "레버리지가 사라지는 건 아니다.\n다만 ‘쉽게 들어가고 1주씩 사는 상품’에서 고위험 거래 문턱이 있는 상품으로 바뀐다.", "내부 검토용 · 투자 권유 아님"),
        ],
    },
}


def build_pack(name: str, spec: dict[str, Any]) -> None:
    folder = ROOT / name
    total = len(spec["slides"])
    plan_slides = []
    for idx, (kind, headline, body, note) in enumerate(spec["slides"], 1):
        if name.startswith("news_"):
            im = news_slide(idx, total, kind, headline, body, note)
        elif name.startswith("incident_"):
            im = incident_slide(idx, total, kind, headline, body, note)
        else:
            im = economy_slide(idx, total, kind, headline, body, note)
        save(im, folder, idx)
        plan_slides.append({
            "slide": idx,
            "role": kind,
            "media_type": "image" if kind == "cover" else "editorial",
            "headline": headline,
            "body": body,
            "source_credit": [s["publisher"] for s in spec["sources"]],
            "rights_status": "publisher_image_unverified_internal_review_only" if kind == "cover" else "original_editorial_layout",
        })
    plan = {
        "schema_version": "owner_review_carousel_plan_v1",
        "account": "A",
        "category": spec["category"],
        "topic": spec["topic"],
        "slide_count": total,
        "review_only": True,
        "publishing_ready": False,
        "slides": plan_slides,
        "sources": spec["sources"],
    }
    (folder / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "review_only": True,
        "publishing_ready": False,
        "factual_basis": "local live collection plus linked publisher articles",
        "comments_used": False,
        "generated_evidence_used": False,
        "publisher_asset_rights": "unverified; cover images are internal review references only",
        "required_before_publish": [
            "re-open every source and recheck claims/timestamps",
            "replace or license publisher images",
            "legal/editorial review for allegation wording",
            "verify current implementation date for market rules",
        ],
        "sources": spec["sources"],
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    make_contact_sheet(folder, total)


def make_contact_sheet(folder: Path, total: int) -> None:
    thumb_w, thumb_h = 270, 338
    cols = 4
    rows = math.ceil(total / cols)
    sheet = Image.new("RGB", (thumb_w * cols, thumb_h * rows), "#E5E7EB")
    for i in range(total):
        im = Image.open(folder / f"slide_{i + 1:02d}.png").convert("RGB")
        im.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x, y = (i % cols) * thumb_w, (i // cols) * thumb_h
        sheet.paste(im, (x, y))
    sheet.save(folder / "contact_sheet.png")


def build_index() -> None:
    cards = []
    for name, spec in PACKS.items():
        folder = ROOT / name
        imgs = "".join(
            f'<figure><img src="{name}/slide_{i:02d}.png" loading="lazy"><figcaption>{i:02d}</figcaption></figure>'
            for i in range(1, len(spec["slides"]) + 1)
        )
        cards.append(f'''<section><div class="head"><div><span>{html.escape(spec["category"])}</span><h2>{html.escape(spec["topic"])}</h2></div><b>{len(spec["slides"])} slides</b></div><div class="strip">{imgs}</div><p>내부 검토용 · 게시 준비 미완료 · 원문/이미지 권리 재검증 필요</p></section>''')
    doc = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Account A · Category Review</title><style>
body{{margin:0;background:#0b0f14;color:#f4f7fb;font-family:"Noto Sans KR","Malgun Gothic",sans-serif}}header{{padding:56px 5vw 30px}}h1{{font-size:46px;margin:0 0 10px}}header p{{color:#99a6b5}}section{{padding:30px 5vw 44px;border-top:1px solid #27313d}}.head{{display:flex;justify-content:space-between;gap:20px;align-items:end}}.head span{{color:#b9ff44;font-weight:800;letter-spacing:.08em}}h2{{font-size:28px;margin:8px 0 0;max-width:850px}}.head b{{color:#99a6b5;white-space:nowrap}}.strip{{display:flex;gap:18px;overflow-x:auto;padding:24px 0 16px;scroll-snap-type:x mandatory}}figure{{margin:0;scroll-snap-align:start;flex:0 0 min(320px,75vw)}}img{{width:100%;display:block;border-radius:16px;box-shadow:0 12px 32px #0008}}figcaption{{padding:7px;color:#718096}}section p{{color:#8997a8}}</style></head><body><header><h1>ACCOUNT A / DESKTOP REVIEW</h1><p>뉴스 해설 · 사건 추적 · 경제 숫자 — 카테고리마다 다른 문법과 리듬</p></header>{''.join(cards)}</body></html>'''
    (ROOT / "index.html").write_text(doc, encoding="utf-8")


if __name__ == "__main__":
    for pack_name, pack_spec in PACKS.items():
        build_pack(pack_name, pack_spec)
    build_index()
    print(json.dumps({"status": "ok", "packs": {k: len(v["slides"]) for k, v in PACKS.items()}}, ensure_ascii=False))
