from __future__ import annotations

import html
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("base_a", ROOT / "build_account_a.py")
base = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(base)

W, H = base.W, base.H
font, wrap, text_block, pill, footer, cover_crop, gradient_overlay = (
    base.font, base.wrap, base.text_block, base.pill, base.footer, base.cover_crop, base.gradient_overlay
)


VISA_SOURCES = [
    {"publisher": "머니투데이", "url": "https://www.mt.co.kr/world/2026/07/16/2026071622465641646"},
    {"publisher": "News1", "url": "https://www.news1.kr/world/usa-canada/6231085"},
    {"publisher": "연합뉴스", "url": "https://www.yna.co.kr/view/AKR20260716213200071?section=international/all"},
]

IRAN_SOURCES = [
    {"publisher": "한국경제", "url": "https://www.hankyung.com/article/202607160517i"},
    {"publisher": "U.S. Senator Ron Wyden / congressional disclosure", "url": "https://www.wyden.senate.gov/news/press-releases/foreign-adversaries-are-using-commercial-location-data-to-target-us-servicemembers-in-the-middle-east-wyden-harrigan-and-12-other-bipartisan-members-of-congress-reveal-members-call-on-department-to-adopt-commonsense-safeguards-to-protect-us-troops"},
]


def visa_slide(i: int, total: int, kind: str, title: str, body: str = "", tag: str = "") -> Image.Image:
    blue, cobalt, cream, ink, red, gray = "#0C3B91", "#125FEA", "#F6F1E6", "#111827", "#F04D4D", "#607087"
    if kind == "cover":
        im = cover_crop(ROOT / "assets" / "visa_mt.jpg")
        im = gradient_overlay(im, 40, 235, (1, 25, 70))
        d = ImageDraw.Draw(im)
        pill(d, (68, 68), "WORLD NEWS · STUDENT VISA", "#F7C948", ink, font(24, True))
        d.text((68, 770), "미국 유학,\n‘학교 다니는 동안’이 끝난다", font=font(37, True), fill="#DDE9FF", spacing=6)
        text_block(d, (68, 935), title, font(76, True), "white", 900, spacing=12)
        footer(d, i, total, "머니투데이 · News1 · 연합뉴스", "#F7C948", "#DDE9FF")
        return im
    im = Image.new("RGB", (W, H), cream)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 154), fill=blue)
    d.text((68, 48), "U.S. VISA / EXPLAINER", font=font(26, True), fill="white")
    d.text((1012, 50), tag, font=font(24, True), fill="#C9D9FF", anchor="ra")
    if kind == "number":
        text_block(d, (68, 220), title, font(61, True), ink, 910, spacing=14)
        d.text((540, 650), body, font=font(205, True), fill=cobalt, anchor="mm")
        d.text((540, 855), "일반적인 최대 체류 허용 기간", font=font(34, True), fill=gray, anchor="mm")
    elif kind == "before_after":
        text_block(d, (68, 220), title, font(61, True), ink, 910, spacing=14)
        left, right = body.split("|")
        d.rounded_rectangle((68, 515, 510, 1030), radius=30, fill="white", outline="#D9DFE8", width=3)
        d.rounded_rectangle((570, 515, 1012, 1030), radius=30, fill=cobalt)
        d.text((112, 565), "기존", font=font(30, True), fill=gray)
        d.text((614, 565), "변경", font=font(30, True), fill="white")
        text_block(d, (112, 650), left, font(42, True), ink, 350, spacing=16)
        text_block(d, (614, 650), right, font(42, True), "white", 350, spacing=16)
    elif kind == "steps":
        text_block(d, (68, 220), title, font(61, True), ink, 910, spacing=14)
        y = 500
        for n, part in enumerate(body.split("|"), 1):
            d.ellipse((68, y, 138, y + 70), fill=cobalt)
            d.text((103, y + 35), str(n), font=font(30, True), fill="white", anchor="mm")
            d.text((172, y + 35), part, font=font(36, True), fill=ink, anchor="lm")
            if n < 3:
                d.line((103, y + 70, 103, y + 148), fill="#A9B9D5", width=5)
            y += 180
    elif kind == "warning":
        text_block(d, (68, 220), title, font(61, True), ink, 910, spacing=14)
        d.rounded_rectangle((68, 510, 1012, 1005), radius=32, fill=red)
        text_block(d, (120, 590), body, font(46, True), "white", 830, spacing=20)
    elif kind == "check":
        text_block(d, (68, 220), title, font(61, True), ink, 910, spacing=14)
        y = 490
        for part in body.split("|"):
            d.rounded_rectangle((68, y, 1012, y + 128), radius=22, fill="white", outline="#D8DEE8", width=2)
            d.rectangle((92, y + 38, 144, y + 90), outline=cobalt, width=5)
            d.text((178, y + 64), part, font=font(33, True), fill=ink, anchor="lm")
            y += 155
    else:
        text_block(d, (68, 220), title, font(61, True), ink, 910, spacing=14)
        text_block(d, (68, 540), body, font(43), ink, 910, spacing=20)
    footer(d, i, total, "최종 규정 보도 기준 · 효력 발생일과 세칙은 공식 공고 재확인", cobalt, gray)
    return im


def iran_slide(i: int, total: int, kind: str, title: str, body: str = "", tag: str = "") -> Image.Image:
    black, red, amber, white, slate, gray = "#090B10", "#D62D3B", "#FFB000", "#F8FAFC", "#18202B", "#9AA6B2"
    if kind == "cover":
        im = cover_crop(ROOT / "assets" / "iran_tracking.jpg")
        im = gradient_overlay(im, 30, 245, (8, 7, 12))
        d = ImageDraw.Draw(im)
        pill(d, (68, 68), "WORLD INCIDENT · DATA TRAIL", amber, black, font(24, True))
        d.text((68, 745), "미사일보다 먼저 움직인 건\n휴대전화의 ‘디지털 배기’였다", font=font(36, True), fill="#FFE6A3", spacing=6)
        text_block(d, (68, 930), title, font(70, True), white, 910, spacing=12)
        footer(d, i, total, "한국경제 보도 · 미 의회 공개자료 보강", amber, "#D5DBE4")
        return im
    im = Image.new("RGB", (W, H), black)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 150), fill=slate)
    d.text((68, 48), f"SIGNAL {i - 1:02d}", font=font(27, True), fill=amber)
    d.text((1012, 50), tag, font=font(24, True), fill=gray, anchor="ra")
    if kind == "flow":
        text_block(d, (68, 220), title, font(59, True), white, 910, spacing=14)
        x = 75
        parts = body.split("|")
        for n, part in enumerate(parts):
            d.rounded_rectangle((x, 575, x + 265, 850), radius=25, fill=["#25303E", red, "#5A3B00"][n])
            text_block(d, (x + 28, 635), part, font(34, True), white, 210, spacing=14)
            if n < 2:
                d.polygon([(x + 290, 690), (x + 340, 720), (x + 290, 750)], fill=amber)
            x += 335
    elif kind == "claim":
        text_block(d, (68, 220), title, font(59, True), white, 910, spacing=14)
        d.rounded_rectangle((68, 525, 1012, 1005), radius=32, fill=slate, outline=red, width=4)
        d.text((112, 575), "기사·공개자료가 말하는 범위", font=font(29, True), fill=amber)
        text_block(d, (112, 655), body, font(40), white, 850, spacing=18)
    elif kind == "separate":
        text_block(d, (68, 220), title, font(59, True), white, 910, spacing=14)
        confirmed, unclear = body.split("|")
        d.rounded_rectangle((68, 510, 1012, 720), radius=26, fill="#15382B")
        d.text((108, 565), "확인", font=font(28, True), fill="#5EF2A4")
        text_block(d, (220, 550), confirmed, font(36, True), white, 720, spacing=14)
        d.rounded_rectangle((68, 765, 1012, 1050), radius=26, fill="#4B1C22")
        d.text((108, 825), "미확인", font=font(28, True), fill="#FF8791")
        text_block(d, (220, 810), unclear, font(36, True), white, 720, spacing=14)
    elif kind == "list":
        text_block(d, (68, 220), title, font(59, True), white, 910, spacing=14)
        y = 505
        for part in body.split("|"):
            d.rounded_rectangle((68, y, 1012, y + 130), radius=20, fill=slate)
            d.ellipse((100, y + 39, 152, y + 91), fill=amber)
            d.text((126, y + 65), "!", font=font(29, True), fill=black, anchor="mm")
            d.text((185, y + 65), part, font=font(33, True), fill=white, anchor="lm")
            y += 155
    else:
        text_block(d, (68, 220), title, font(59, True), white, 910, spacing=14)
        text_block(d, (68, 540), body, font(42), white, 910, spacing=20)
    footer(d, i, total, "추적 정황 ≠ 공격 성공 인과 · 기사 근거와 추정 분리", amber, gray)
    return im


PACKS: dict[str, dict[str, Any]] = {
    "world_news_visa": {
        "category": "world_news",
        "topic": "미국 외국학생 F-1 체류 최대 4년 최종 규정",
        "sources": VISA_SOURCES,
        "slides": [
            ("cover", "F-1 체류 최대 4년\n한국 유학생은 뭐가 달라지나", "", ""),
            ("number", "규정의 핵심 숫자", "4년", "핵심"),
            ("before_after", "‘재학 중이면 계속’에서\n고정 기간으로", "학업을 계속하면\n정규과정 종료까지\n체류 가능|일반적으로 최대 4년\n그 이후 별도\n연장 승인 필요", "전후 비교"),
            ("steps", "4년을 넘는 과정이라면", "현재 허용기간 확인|만료 전 DHS에 체류 연장 신청|승인 결과와 학교 기록 함께 관리", "연장 절차"),
            ("warning", "박사·장기과정이\n가장 먼저 체감할 변화", "과정이 4년을 넘는다고\n자동으로 체류가 이어지는 게 아니라\n연장 심사를 한 번 더 거쳐야 한다.", "장기과정"),
            ("body", "왜 바꿨나", "미 국토안보부는 학생비자 악용 불법체류 방지와 국가안보 우려 해소를 이유로 들었다고 복수 매체가 보도했다.", "정부 설명"),
            ("check", "한국 유학생이 지금\n확인할 세 가지", "내 I-94의 체류 종료 표시|I-20 과정 종료일과 실제 졸업 예상일|학교 국제학생 담당부서의 시행 안내", "실무 확인"),
            ("body", "아직 단정하면 안 되는 것", "모든 기존 학생에게 언제부터 어떤 방식으로 적용되는지는 공식 효력 발생일·경과조치·세부 신청 절차를 다시 확인해야 한다.", "적용 공백"),
        ],
    },
    "world_incident_iran_tracking": {
        "category": "world_incident",
        "topic": "이란전 중 미군 휴대전화 위치 추적 시도와 로밍·광고기술 악용 정황",
        "sources": IRAN_SOURCES,
        "slides": [
            ("cover", "전화기를 해킹하지 않고\n미군 위치를 쫓았다?", "", ""),
            ("claim", "보도된 핵심 정황", "이란전 전후 미군을 겨냥한 위치 추적 시도가 포착됐으며, 로밍망과 상업용 광고 데이터가 경로로 지목됐다.", "보도 범위"),
            ("flow", "위치는 이렇게 새어 나갈 수 있다", "휴대전화·앱\n식별자 생성|로밍망·광고망\n위치 신호 축적|데이터 분석\n이동 패턴 추정", "가능 경로"),
            ("body", "핵심은 ‘전화기 해킹’만이 아니다", "스마트폰은 위치·광고 식별자·접속 흔적 같은 이른바 디지털 배기를 남긴다. 상업 데이터만으로도 부대 이동 패턴을 추정할 위험이 있다는 설명이다.", "공개 설명"),
            ("claim", "미 의회 공개자료가\n확인한 더 넓은 문제", "미 중부사령부는 적대 세력이 상업용 위치 데이터를 이용해 전장 내 미군을 감시하거나 겨냥하려 했다는 복수 위협 보고를 받았다고 의회에 알렸다.", "공식 보강"),
            ("separate", "여기서 선을 그어야 한다", "위치 데이터 악용 위협과 추적 시도 정황|그 데이터가 실제 미사일·드론 공격 좌표로 직접 이어졌다는 인과", "확인/미확인"),
            ("body", "왜 광고기술이\n군사 보안 문제가 됐나", "광고를 맞춤 노출하려 모은 데이터가 개인의 반복 이동·체류 지점을 보여줄 수 있기 때문이다. 전장에서는 그 반복이 기지와 부대 움직임이 된다.", "구조적 위험"),
            ("list", "공개자료가 제시한\n방어 방향", "광고 식별자·위치공유 차단|정부 지급 기기의 추적 기능 축소|상업 위치데이터 구매·판매 통제", "대응"),
            ("body", "이 사건의 한 줄 결론", "전쟁터의 스마트폰은 통신수단이면서 위치 센서다. 다만 ‘추적 시도’와 ‘공격 성공’을 같은 사실처럼 말하면 안 된다.", "정리"),
        ],
    },
}


def contact_sheet(folder: Path, total: int) -> None:
    tw, th, cols = 270, 338, 4
    rows = math.ceil(total / cols)
    out = Image.new("RGB", (tw * cols, th * rows), "#E5E7EB")
    for n in range(1, total + 1):
        im = Image.open(folder / f"slide_{n:02d}.png").convert("RGB")
        im.thumbnail((tw, th), Image.Resampling.LANCZOS)
        out.paste(im, (((n - 1) % cols) * tw, ((n - 1) // cols) * th))
    out.save(folder / "contact_sheet.png")


def build_pack(name: str, cfg: dict[str, Any]) -> None:
    folder = ROOT / name
    folder.mkdir(parents=True, exist_ok=True)
    total = len(cfg["slides"])
    slides = []
    for i, (kind, title, body, tag) in enumerate(cfg["slides"], 1):
        im = visa_slide(i, total, kind, title, body, tag) if name == "world_news_visa" else iran_slide(i, total, kind, title, body, tag)
        im.save(folder / f"slide_{i:02d}.png", quality=95)
        slides.append({
            "slide": i, "role": kind, "media_type": "image" if kind == "cover" else "editorial",
            "headline": title, "body": body,
            "source_credit": [s["publisher"] for s in cfg["sources"]],
            "rights_status": "publisher_image_unverified_internal_review_only" if kind == "cover" else "original_editorial_layout",
        })
    plan = {"schema_version": "owner_review_carousel_plan_v1", "account": "A", "category": cfg["category"], "topic": cfg["topic"], "slide_count": total, "review_only": True, "publishing_ready": False, "slides": slides, "sources": cfg["sources"]}
    (folder / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "review_only": True, "publishing_ready": False, "comments_used": False,
        "generated_evidence_used": False,
        "publisher_asset_rights": "unverified; internal review only",
        "claim_boundary": "reported attempts and official threat disclosures are separated from unconfirmed attack causation",
        "required_before_publish": ["recheck official effective date and transition rules", "license or replace publisher imagery", "re-open every source", "legal/editorial review for military and immigration claims"],
        "sources": cfg["sources"],
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    contact_sheet(folder, total)


def rebuild_index() -> None:
    sections = []
    for plan_path in sorted(ROOT.glob("*/plan.json")):
        cfg = json.loads(plan_path.read_text(encoding="utf-8"))
        name = plan_path.parent.name
        imgs = "".join(f'<figure><img src="{name}/slide_{i:02d}.png" loading="lazy"><figcaption>{i:02d}</figcaption></figure>' for i in range(1, cfg["slide_count"] + 1))
        sections.append(f'<section><div class="head"><div><span>{html.escape(cfg["category"])}</span><h2>{html.escape(cfg["topic"])}</h2></div><b>{cfg["slide_count"]} slides</b></div><div class="strip">{imgs}</div><p>내부 검토용 · 게시 준비 미완료 · 원문/이미지 권리 재검증 필요</p></section>')
    page = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Account A · Category Review</title><style>body{{margin:0;background:#0b0f14;color:#f4f7fb;font-family:"Noto Sans KR","Malgun Gothic",sans-serif}}header{{padding:56px 5vw 30px}}h1{{font-size:46px;margin:0 0 10px}}header p{{color:#99a6b5}}section{{padding:30px 5vw 44px;border-top:1px solid #27313d}}.head{{display:flex;justify-content:space-between;gap:20px;align-items:end}}.head span{{color:#b9ff44;font-weight:800;letter-spacing:.08em}}h2{{font-size:28px;margin:8px 0 0;max-width:850px}}.head b{{color:#99a6b5;white-space:nowrap}}.strip{{display:flex;gap:18px;overflow-x:auto;padding:24px 0 16px;scroll-snap-type:x mandatory}}figure{{margin:0;scroll-snap-align:start;flex:0 0 min(320px,75vw)}}img{{width:100%;display:block;border-radius:16px;box-shadow:0 12px 32px #0008}}figcaption{{padding:7px;color:#718096}}section p{{color:#8997a8}}</style></head><body><header><h1>ACCOUNT A / DESKTOP REVIEW</h1><p>국내·세계뉴스 · 국내·세계사건 · 경제 — 다섯 카테고리, 서로 다른 편집 문법</p></header>{''.join(sections)}</body></html>'''
    (ROOT / "index.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    for name, cfg in PACKS.items():
        build_pack(name, cfg)
    rebuild_index()
    print(json.dumps({"status": "ok", "packs": {k: len(v["slides"]) for k, v in PACKS.items()}}, ensure_ascii=False))
