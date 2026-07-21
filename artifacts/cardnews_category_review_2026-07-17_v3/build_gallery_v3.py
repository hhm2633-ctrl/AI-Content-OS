from __future__ import annotations

import html
import json
import math
import shutil
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "cardnews_category_review_2026-07-17_v2"
COLLECTION = ROOT / "collection.json"
INPUTS = ROOT / "inputs"
W, H = 1080, 1350
FONT_REG = Path(r"C:\Windows\Fonts\malgun.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\malgunbd.ttf")


PACKS = {
    "account_a_gibraltar": {
        "account": "A",
        "category": "세계뉴스",
        "title": "117년 된 육로 장벽이 열린 날",
        "bodies": [
            "지브롤터와 스페인 사이의 육로 검문 시설이 7월 15일 철거됐다. 브렉시트 이후 이어진 협상이 실제 통행 변화로 이어진 첫날이다.",
            "지브롤터는 영국령이지만 육지는 스페인 라리네아와 바로 맞닿아 있다. 국경은 주민들의 출퇴근과 생활을 매일 가르던 선이었다.",
            "현장에서는 장벽과 검색대를 걷어내는 작업이 밤새 진행됐다. 다음 날부터 사람과 차량은 상시 검문 없이 오가기 시작했다.",
            "예전에는 육로를 지날 때마다 여권 확인을 받아야 했다. 이제 일상 통행의 가장 눈에 띄는 장벽이 사라졌다.",
            "스페인 쪽에서 지브롤터로 출근하는 사람은 하루 약 1만5천 명이다. 이번 변화는 관광보다 먼저 생활권의 변화다.",
            "검문이 완전히 없어진 것은 아니다. 외부에서 들어오는 여행객 심사는 공항과 항만 쪽으로 옮겨간다.",
            "영유권 문제가 해결된 것은 아니며 주권도 그대로다. 달라진 것은 육로의 상시 검문과 물리적 장벽이다.",
        ],
        "caption": "117년 동안 지브롤터와 스페인 사이를 가르던 육로 장벽이 7월 15일 철거됐습니다. 브렉시트 이후 4년 넘게 이어진 협상 끝에 약 1만5천 명의 통근자가 매일 지나던 길의 상시 검문이 멈춘 것입니다. 다만 영유권과 주권 문제가 해결된 것은 아니며, 외부 입국 심사는 공항과 항만으로 이동합니다.\n\n자료: 영국 정부·지브롤터 정부 공식 발표, AP 교차확인\n※ 내부 검토본이며 이미지 사용권과 최신 사실을 게시 전 다시 확인해야 합니다.",
    },
    "account_b_salon": {
        "account": "B",
        "category": "현실사연·이슈",
        "title": "17만 원 미용실 바리깡 피해 제보",
        "bodies": [
            "제보자는 새치 염색을 받으러 갔다가 예상하지 못한 짧은 커트를 받았다고 주장했다. 시술 전후의 차이가 논란의 출발점이다.",
            "처음 요청한 것은 새치 염색이었다는 게 제보자의 설명이다. 이때까지는 길이와 스타일을 크게 바꿀 계획이 없었다.",
            "상담 중 미용사가 투블럭 스타일을 제안했다고 한다. 제보자는 정확히 어느 정도로 자르는지 충분히 이해하지 못했다고 주장한다.",
            "동의 직후 바리깡으로 뒤통수를 한 번에 밀었다는 설명이다. 되돌리기 어려운 시술에서 설명과 합의가 핵심 쟁점이 됐다.",
            "거울로 결과를 확인한 제보자는 당황했다고 밝혔다. 공개된 전후 화면은 온라인 반응을 크게 만든 장면이다.",
            "제보자는 현장에서 17만 원을 결제한 뒤 귀가해 다시 항의했다고 설명했다. 결제 사실이 시술 동의를 의미하는지를 두고도 반응이 갈렸다.",
            "미용실 측은 실수가 아니라 콘셉트였다는 취지로 답했다고 전해졌다. 현재는 제보 원문 단계라 양측 입장과 사실관계 재확인이 필요하다.",
        ],
        "caption": "새치 염색을 받으러 간 손님이 상담 도중 투블럭 제안을 받아들인 뒤, 예상하지 못한 길이로 머리가 잘렸다고 주장했습니다. 제보자는 현장에서 17만 원을 결제한 후 다시 항의했지만 미용실 측은 실수가 아니라는 취지로 답했다고 설명했습니다.\n\n여러분이라면 되돌릴 수 없는 시술 전에 어디까지 설명받아야 한다고 생각하나요?\n※ 소유자 제공 공개 게시물 캡처를 정리한 내부 검토본입니다. 양측 입장과 사실관계, 이미지 인용 범위를 게시 전 확인해야 합니다.",
    },
    "account_c_dior": {
        "account": "C",
        "category": "패션·시즌",
        "title": "DIOR MEN 2027 S/S",
        "bodies": [
            "디올 맨 2027 S/S는 익숙한 남성복의 비율과 표면을 다시 조립한다. 사진을 넘기며 이번 시즌의 거리감부터 확인한다.",
            "정장과 스포츠웨어의 익숙한 요소를 그대로 반복하지 않았다. 크기와 질감의 균형을 바꿔 낯선 인상을 만들었다.",
            "턱시도 재킷은 몸에 붙기보다 크게 떠 있는 실루엣으로 등장했다. 옷과 몸 사이의 여백이 이번 시즌을 읽는 첫 단서다.",
            "하운즈투스는 직조 무늬가 아니라 프린트처럼 다뤄졌다. 클래식한 패턴이 더 평평하고 그래픽한 표면으로 바뀐다.",
            "정교한 테일러링 위에는 일부러 거칠게 보이는 질감이 겹친다. 한 벌 안에서 완성과 미완성의 감각이 동시에 보인다.",
            "색은 낮게 눌렀지만 소재의 굴곡과 부피는 크게 남겼다. 강한 색보다 표면과 실루엣이 먼저 시선을 잡는다.",
            "이 룩은 커진 비율과 거친 표면, 낮은 색조를 한 장면에 모은다. 2027 S/S의 핵심을 가장 빠르게 보여주는 장면이다.",
        ],
        "caption": "DIOR MEN 2027 S/S는 익숙한 남성복을 완전히 버리기보다 비율과 표면을 다시 조립합니다. 몸에서 크게 떨어지는 턱시도, 프린트처럼 처리한 하운즈투스, 정교함 위에 얹힌 거친 질감이 이번 시즌의 분위기를 만듭니다.\n\n시즌 콘셉트를 가장 잘 보여주는 장면만 짧게 골랐습니다. 사진이 먼저 보이고 설명은 이해에 필요한 만큼만 붙였습니다.\n\n자료: DIOR 공식 2027 S/S 쇼\n※ 실제 런웨이 이미지의 게시 권리는 별도 확인이 필요합니다.",
    },
    "account_c_valentino": {
        "account": "C",
        "category": "뷰티·향수",
        "title": "Valentino VENDETTA",
        "bodies": [
            "발렌티노 뷰티가 6년 만에 새 향수 듀오 벤데타를 공개했다. DONNA와 UOMO를 하나의 뜨거운 캠페인으로 묶었다.",
            "두 향은 같은 캠페인 안에서 서로 다른 온도를 보여준다. 패키지의 강한 레드와 블랙 대비가 첫 장면을 만든다.",
            "DONNA는 튜베로즈와 레드 오렌지를 중심으로 전개된다. 밝은 첫인상 뒤에 꽃의 농도가 길게 남는 구성을 내세운다.",
            "튜베로즈는 DONNA의 중심을 잡는 꽃이다. 흰 꽃의 밝음과 짙은 잔향을 가까운 질감 이미지로 보여준다.",
            "UOMO는 진저와 시나몬 리큐어의 대비를 전면에 둔다. 차가운 시작과 달콤한 열기가 빠르게 교차한다.",
            "진저의 날카로운 첫 향이 UOMO의 속도를 만든다. 짧은 영상에서는 차가운 빛에서 따뜻한 빛으로 전환하기 좋다.",
            "레드 오렌지는 DONNA의 첫인상을 더 선명하게 만든다. 과육과 병의 붉은 색을 빠르게 교차하면 시선 정지력이 커진다.",
            "현재 공개된 제품과 캠페인 이미지가 첫 인상을 완성한다. 후속 필름은 같은 자산을 짧은 모션과 릴스로 확장하기 좋다.",
        ],
        "caption": "Valentino Beauty가 6년 만에 새 향수 듀오 VENDETTA를 공개했습니다. DONNA는 튜베로즈와 레드 오렌지, UOMO는 진저와 시나몬 리큐어를 중심으로 서로 다른 열기를 표현합니다.\n\n제품 병, 원료의 질감, 강한 레드 컬러가 먼저 보이도록 구성했고 설명은 향의 방향을 이해하는 정도로 줄였습니다. 다음 단계에서는 공식 캠페인 필름을 활용한 짧은 모션 컷으로 확장할 수 있습니다.\n\n자료: Valentino Beauty 공식 제품 페이지·공식 배포 자료\n※ 제품 이미지와 캠페인 영상의 소셜 게시 권리는 별도 확인이 필요합니다.",
    },
}

CATEGORY_LABELS = {
    "fashion_season": "패션 시즌",
    "fashion_trend": "패션 트렌드",
    "celebrity_style": "셀럽 스타일",
    "beauty_look": "뷰티 룩",
    "beauty_makeup": "뷰티 메이크업",
    "beauty_hair": "뷰티 헤어",
    "beauty_nail": "네일",
    "beauty_skincare": "스킨케어",
    "beauty_body": "바디 뷰티",
    "beauty_hair_fragrance": "헤어·바디 미스트",
    "beauty_device": "뷰티 디바이스",
    "beauty_makeup_collection": "뷰티 컬렉션",
    "fragrance": "향수",
    "fragrance_men": "남성 향수",
    "fragrance_body": "바디 프래그런스",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REG), size)


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        trial = current + char
        if draw.textbbox((0, 0), trial, font=fnt)[2] <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines[:3]


def add_lower_third(path: Path, body: str, accent: str) -> None:
    image = Image.open(path).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    top = 1060
    draw.rectangle((0, top, W, H), fill=(8, 10, 14, 242))
    draw.rectangle((0, top, 16, H), fill=accent)
    draw.text((54, top + 30), "본문", font=font(19, True), fill=accent)
    y = top + 68
    for line in wrap(draw, body, font(27), 965):
        draw.text((54, y), line, font=font(27), fill=(245, 245, 242, 255))
        y += 41
    draw.text((54, H - 34), "1–2문장 하단 본문 · 내부 검토", font=font(16), fill=(170, 176, 188, 255), anchor="ld")
    Image.alpha_composite(image, overlay).convert("RGB").save(path, optimize=True)


def contact_sheet(folder: Path, total: int) -> None:
    tw, th, cols = 270, 338, 4
    rows = math.ceil(total / cols)
    sheet = Image.new("RGB", (tw * cols, th * rows), "#14171C")
    for index in range(1, total + 1):
        image = Image.open(folder / f"slide_{index:02d}.png").convert("RGB")
        image.thumbnail((tw, th), Image.Resampling.LANCZOS)
        sheet.paste(image, (((index - 1) % cols) * tw, ((index - 1) // cols) * th))
    sheet.save(folder / "contact_sheet.png", optimize=True)


def prepare_packs() -> None:
    accents = {"A": "#F2A900", "B": "#FF3B30", "C": "#E64178"}
    for slug, spec in PACKS.items():
        src = SOURCE / slug
        dst = ROOT / slug
        shutil.copytree(src, dst, dirs_exist_ok=True)
        plan_path = dst / "plan.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        for slide, body in zip(plan["slides"], spec["bodies"], strict=True):
            slide["lower_third_body"] = body
            slide["body_sentence_count"] = 2 if body.count(".") >= 2 else 1
        plan["feed_caption"] = spec["caption"]
        plan["schema_version"] = "full_collection_owner_review_v3"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        for index, body in enumerate(spec["bodies"], 1):
            add_lower_third(dst / f"slide_{index:02d}.png", body, accents[spec["account"]])
        contact_sheet(dst, len(spec["bodies"]))


def merge_collection() -> dict:
    documents = [
        json.loads((INPUTS / name).read_text(encoding="utf-8"))
        for name in ("account_a.json", "account_b.json", "account_c.json")
    ]
    candidates = [item for document in documents for item in document["candidates"]]
    exclusions = [item for document in documents for item in document.get("exclusion_ledger", [])]
    for item in candidates + exclusions:
        raw_category = item.get("category", "미분류")
        item["raw_category"] = raw_category
        item["category"] = CATEGORY_LABELS.get(raw_category, raw_category)
    def coverage_text(value: object) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return " ".join(str(item) for item in value)
        if isinstance(value, dict):
            return " ".join(f"{key}: {coverage_text(item)}" for key, item in value.items())
        return str(value)

    data = {
        "schema_version": "full_visible_collection_v3",
        "as_of": "2026-07-17T11:30:00+09:00",
        "candidates": candidates,
        "exclusion_ledger": exclusions,
        "source_counts": {document.get("account", f"lane_{index}"): document.get("counts", {}) for index, document in enumerate(documents, 1)},
        "coverage_note": " / ".join(coverage_text(document["coverage_note"]) for document in documents),
    }
    COLLECTION.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def build_index() -> None:
    data = merge_collection()
    candidates = data["candidates"] + data.get("exclusion_ledger", [])
    counts = Counter(item["account"] for item in candidates)
    category_counts = Counter(item["category"] for item in candidates)
    collection_json = json.dumps(candidates, ensure_ascii=False).replace("</", "<\\/")
    category_options = "".join(
        f'<option value="{html.escape(category)}">{html.escape(category)} · {count}</option>'
        for category, count in sorted(category_counts.items())
    )
    pack_html = "".join(
        f'''<article class="pack account-{spec["account"].lower()}">
          <img src="{slug}/contact_sheet.png" alt="{html.escape(spec["title"])} contact sheet" loading="lazy">
          <div class="pack-copy"><span>ACCOUNT {spec["account"]} · {html.escape(spec["category"])}</span>
          <h3>{html.escape(spec["title"])}</h3><p>{len(spec["bodies"])}장 · 카드마다 하단 본문 1–2문장 적용</p>
          <details><summary>Instagram 피드 본문 보기</summary><pre>{html.escape(spec["caption"])}</pre></details>
          <a href="{slug}/slide_01.png">첫 장</a> <a href="{slug}/plan.json">전체 본문·출처</a></div></article>'''
        for slug, spec in PACKS.items()
    )
    production_section = f'''<section><h2>2. 이전 제작본 최신 교정</h2><p class="section-note">새 후보를 임의 제작하지 않고 소유자 선별을 기다립니다. 이미 검토한 4개 제작본에는 요청한 카드 하단 본문과 별도 Instagram 피드 본문을 먼저 반영했습니다.</p><div class="packs">{pack_html}</div></section>'''
    page = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>2026-07-17 CardNews 전체 최신 후보 v3</title><style>
:root{{--bg:#080a0e;--panel:#141821;--panel2:#1c222d;--text:#f7f8fa;--muted:#aeb7c5;--line:#303744;--a:#f2a900;--b:#ff4c42;--c:#e64178}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:"Malgun Gothic",sans-serif}}header{{padding:56px 5vw 34px;background:radial-gradient(circle at 8% 0,#294775 0,transparent 45%);border-bottom:1px solid var(--line)}}h1{{font-size:clamp(36px,5vw,66px);letter-spacing:-3px;margin:0 0 12px}}header p{{max-width:1050px;color:var(--muted);font-size:18px;line-height:1.7}}.warning{{display:inline-block;background:#4b2525;color:#ffc8c8;padding:10px 15px;border-radius:999px;font-weight:800}}.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-top:25px;max-width:900px}}.stat{{background:#111722cc;border:1px solid var(--line);padding:17px;border-radius:16px}}.stat b{{display:block;font-size:31px}}nav{{position:sticky;top:0;z-index:3;display:flex;gap:10px;flex-wrap:wrap;padding:14px 5vw;background:#090c11ee;backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}}button,select,input{{background:#171d27;color:#fff;border:1px solid #394252;border-radius:12px;padding:11px 13px;font:inherit}}button.active{{background:#2f6fed;border-color:#75a1ff}}main{{padding:34px 5vw 70px}}section{{margin-bottom:60px}}h2{{font-size:34px;letter-spacing:-1.5px;margin-bottom:8px}}.section-note{{color:var(--muted);line-height:1.6;margin-bottom:22px}}#candidate-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:16px}}.candidate{{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:19px;display:flex;flex-direction:column;gap:11px}}.candidate[data-account="A"]{{border-top:4px solid var(--a)}}.candidate[data-account="B"]{{border-top:4px solid var(--b)}}.candidate[data-account="C"]{{border-top:4px solid var(--c)}}.candidate.excluded{{outline:2px solid #a43535;background:#281719}}.eyebrow{{display:flex;justify-content:space-between;color:#8fd1ff;font-weight:800;font-size:14px}}.candidate h3{{font-size:22px;line-height:1.35;margin:0}}.candidate p{{color:#c5ccd6;line-height:1.55;margin:0}}.meta{{color:#919baa;font-size:14px}}.tags{{display:flex;gap:7px;flex-wrap:wrap}}.tag{{font-size:12px;background:#252c38;border-radius:999px;padding:6px 9px}}.sources a{{color:#9bc2ff;font-size:13px;word-break:break-all}}.choices{{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:auto}}.choices button{{font-size:13px;padding:9px 4px}}.choices button.selected{{background:#2f6fed;border-color:#83aaff}}.packs{{display:grid;grid-template-columns:repeat(auto-fit,minmax(390px,1fr));gap:22px}}.pack{{background:var(--panel);border:1px solid var(--line);border-radius:20px;overflow:hidden}}.pack img{{display:block;width:100%;background:#111}}.pack-copy{{padding:21px}}.pack-copy span{{font-weight:900;color:#8fd1ff}}.pack h3{{font-size:27px;margin:7px 0}}.pack p{{color:var(--muted)}}.pack a{{color:#9bc2ff;font-weight:800;margin-right:12px}}details{{margin:14px 0;background:var(--panel2);padding:12px;border-radius:12px}}summary{{cursor:pointer;font-weight:800}}pre{{white-space:pre-wrap;line-height:1.65;font-family:inherit;color:#d8dde5}}footer{{padding:28px 5vw 55px;border-top:1px solid var(--line);color:var(--muted);line-height:1.7}}@media(max-width:650px){{nav input{{width:100%}}.choices{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body><header><h1>오늘 수집한 것, 전부</h1>
<p>2026년 7월 17일 11시대 KST 공개 웹 스냅샷입니다. 제가 먼저 골라서 숨기지 않았습니다. 중복은 묶음으로, 민감 소재는 제외대장으로, 권리·팩트 미확인은 검증 필요로 그대로 표시했습니다.</p>
<span class="warning">내부 선별 전용 · 게시/업로드 불가</span><div class="stats"><div class="stat"><b>{len(candidates)}</b>보이는 전체 항목</div><div class="stat"><b>{counts['A']}</b>Account A</div><div class="stat"><b>{counts['B']}</b>Account B</div><div class="stat"><b>{counts['C']}</b>Account C</div></div></header>
<nav><button class="account-filter active" data-value="ALL">전체</button><button class="account-filter" data-value="A">A 뉴스</button><button class="account-filter" data-value="B">B 연애·썰</button><button class="account-filter" data-value="C">C 패션·뷰티</button><select id="category"><option value="ALL">모든 카테고리</option>{category_options}</select><input id="search" placeholder="제목·맥락 검색"><button id="export">내 선택 JSON 저장</button></nav>
<main><section><h2>1. 전체 후보와 제외대장</h2><p class="section-note">KEEP·REJECT·RECLASSIFY·MAKE를 누르면 Chrome 로컬 저장소에 기록됩니다. 중복과 제외 항목도 기본 화면에서 숨기지 않습니다.</p><div id="candidate-grid"></div></section>
{production_section}
<section><h2>3. 수집 경계</h2><p class="section-note">{html.escape(data['coverage_note'])}</p></section></main><footer>실제 게시·Git·자동화·Commerce·Shorts 작업은 수행하지 않았습니다. 선택 결과는 사용자가 내보낸 JSON을 다시 전달받은 뒤에만 학습 기록과 신규 제작에 반영합니다.</footer>
<script id="dataset" type="application/json">{collection_json}</script><script>
const data=JSON.parse(document.getElementById('dataset').textContent);let account='ALL';const grid=document.getElementById('candidate-grid');const saved=JSON.parse(localStorage.getItem('cardnews-review-v3')||'{{}}');
function esc(s){{return String(s??'').replace(/[&<>\"]/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}}[m]))}}
function render(){{const cat=document.getElementById('category').value,q=document.getElementById('search').value.toLowerCase();grid.innerHTML='';data.filter(x=>(account==='ALL'||x.account===account)&&(cat==='ALL'||x.category===cat)&&(!q||JSON.stringify(x).toLowerCase().includes(q))).forEach(x=>{{const card=document.createElement('article');card.className='candidate '+(x.status==='HARD_EXCLUDE_NOT_HIDDEN'?'excluded':'');card.dataset.account=x.account;const urls=x.urls||[x.url].filter(Boolean);card.innerHTML=`<div class="eyebrow"><span>ACCOUNT ${{esc(x.account)}} · ${{esc(x.category)}}</span><span>${{esc(x.id)}}</span></div><h3>${{esc(x.title)}}</h3><p>${{esc(x.context||x.reason||'')}}</p><div class="meta">${{esc(x.published_at||x.currentness||'날짜 확인 필요')}}</div><div class="tags"><span class="tag">${{esc(x.status||'OWNER_UNLABELED')}}</span><span class="tag">${{esc(x.duplicate_group||'독립 후보')}}</span></div><p class="meta">시각: ${{esc(x.visual_assets||x.visual_direction||'확인 필요')}}</p><p class="meta">주의: ${{esc(x.risk||x.rights_risk||'게시 전 검증')}}</p><div class="sources">${{urls.map((u,i)=>`<a href="${{esc(u)}}" target="_blank" rel="noreferrer">출처 ${{i+1}}</a>`).join(' · ')}}</div><div class="choices">${{['KEEP','REJECT','RECLASSIFY','MAKE'].map(v=>`<button data-choice="${{v}}" class="${{saved[x.id]===v?'selected':''}}">${{v}}</button>`).join('')}}</div>`;card.querySelectorAll('[data-choice]').forEach(b=>b.onclick=()=>{{saved[x.id]=b.dataset.choice;localStorage.setItem('cardnews-review-v3',JSON.stringify(saved));render()}});grid.appendChild(card)}})}}
document.querySelectorAll('.account-filter').forEach(b=>b.onclick=()=>{{document.querySelectorAll('.account-filter').forEach(x=>x.classList.remove('active'));b.classList.add('active');account=b.dataset.value;render()}});document.getElementById('category').onchange=render;document.getElementById('search').oninput=render;document.getElementById('export').onclick=()=>{{const blob=new Blob([JSON.stringify({{exported_at:new Date().toISOString(),decisions:saved}},null,2)],{{type:'application/json'}}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='cardnews_owner_decisions_2026-07-17.json';a.click();URL.revokeObjectURL(a.href)}};render();
</script></body></html>'''
    (ROOT / "index.html").write_text(page, encoding="utf-8")
    collection_only = page.replace(production_section, "").replace("1. 전체 후보와 제외대장", "전체 후보와 제외대장").replace("3. 수집 경계", "수집 경계")
    collection_only = collection_only.replace("<title>2026-07-17 CardNews 전체 최신 후보 v3</title>", "<title>2026-07-17 최신 수집 전체 보고</title>")
    collection_only = collection_only.replace("이전 제작본 최신 교정", "선별 전 수집 보고")
    (ROOT / "collection_review.html").write_text(collection_only, encoding="utf-8")


if __name__ == "__main__":
    ROOT.mkdir(parents=True, exist_ok=True)
    prepare_packs()
    build_index()
    print(json.dumps({"status": "ok", "gallery": str(ROOT / "index.html")}, ensure_ascii=False))
