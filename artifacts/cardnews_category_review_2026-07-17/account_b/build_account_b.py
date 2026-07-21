from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
W, H = 1080, 1350
FONT_BOLD = Path(r"C:\Windows\Fonts\malgunbd.ttf")
FONT_REG = Path(r"C:\Windows\Fonts\malgun.ttf")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REG), size)


def fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, start: int, minimum: int, bold: bool = False):
    for size in range(start, minimum - 1, -2):
        f = font(size, bold)
        words = text.split()
        lines, line = [], ""
        for word in words:
            trial = f"{line} {word}".strip()
            if draw.textbbox((0, 0), trial, font=f)[2] <= max_width:
                line = trial
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        if max(draw.textbbox((0, 0), ln, font=f)[2] for ln in lines) <= max_width:
            return f, "\n".join(lines)
    return font(minimum, bold), text


def cover_crop(img: Image.Image, size=(W, H), focus_y=0.5) -> Image.Image:
    img = img.convert("RGB")
    scale = max(size[0] / img.width, size[1] / img.height)
    nw, nh = round(img.width * scale), round(img.height * scale)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    x = max(0, (nw - size[0]) // 2)
    y = max(0, min(nh - size[1], int((nh - size[1]) * focus_y)))
    return img.crop((x, y, x + size[0], y + size[1]))


def panel(sheet: Image.Image, index: int) -> Image.Image:
    # Generated sheets are deliberate 2x2 illustration grids.
    x0 = 0 if index % 2 == 0 else sheet.width // 2
    y0 = 0 if index < 2 else sheet.height // 2
    x1 = sheet.width // 2 if index % 2 == 0 else sheet.width
    y1 = sheet.height // 2 if index < 2 else sheet.height
    return sheet.crop((x0 + 8, y0 + 8, x1 - 8, y1 - 8))


def gradient_overlay(img: Image.Image, top_alpha=25, bottom_alpha=230) -> Image.Image:
    rgba = img.convert("RGBA")
    overlay = Image.new("RGBA", rgba.size)
    p = overlay.load()
    for y in range(H):
        a = int(top_alpha + (bottom_alpha - top_alpha) * (y / H) ** 1.8)
        for x in range(W):
            p[x, y] = (5, 7, 12, a)
    return Image.alpha_composite(rgba, overlay).convert("RGB")


def footer(draw, source: str, number: str, color=(235, 235, 235)):
    draw.text((62, H - 66), source, font=font(24), fill=color)
    tw = draw.textbbox((0, 0), number, font=font(24, True))[2]
    draw.text((W - 62 - tw, H - 66), number, font=font(24, True), fill=color)


def image_slide(image: Image.Image, eyebrow: str, headline: str, body: str, source: str, number: str,
                accent=(255, 83, 71), focus_y=0.5, reconstruction=False) -> Image.Image:
    canvas = gradient_overlay(cover_crop(image, focus_y=focus_y))
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((58, 64, 58 + 290, 114), radius=20, fill=accent)
    d.text((78, 74), eyebrow, font=font(24, True), fill="white")
    if reconstruction:
        d.rounded_rectangle((58, 126, 352, 172), radius=18, fill=(15, 15, 20, 205))
        d.text((76, 136), "AI 재구성 · 사연 기반", font=font(21, True), fill=(245, 224, 181))
    hf, wrapped = fit_text(d, headline, W - 124, 74, 48, True)
    box = d.multiline_textbbox((0, 0), wrapped, font=hf, spacing=14)
    headline_y = H - 390 - (box[3] - box[1])
    d.multiline_text((62, headline_y), wrapped, font=hf, fill="white", spacing=14)
    if body:
        bf, body_wrapped = fit_text(d, body, W - 124, 34, 28)
        d.multiline_text((62, H - 282), body_wrapped, font=bf, fill=(236, 236, 236), spacing=10)
    footer(d, source, number)
    return canvas


def text_slide(eyebrow: str, headline: str, body: str, source: str, number: str,
               bg=(247, 242, 233), fg=(30, 28, 27), accent=(211, 54, 48), note="") -> Image.Image:
    canvas = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(canvas)
    d.rectangle((0, 0, 24, H), fill=accent)
    d.text((70, 76), eyebrow, font=font(27, True), fill=accent)
    hf, wrapped = fit_text(d, headline, W - 150, 72, 48, True)
    d.multiline_text((70, 210), wrapped, font=hf, fill=fg, spacing=14)
    y = d.multiline_textbbox((70, 210), wrapped, font=hf, spacing=14)[3] + 74
    bf, body_wrapped = fit_text(d, body, W - 150, 38, 28)
    dark_bg = sum(bg) / 3 < 105
    body_color = (212, 214, 220) if dark_bg else (70, 66, 64)
    footer_color = (205, 207, 214) if dark_bg else (85, 80, 78)
    d.multiline_text((70, y), body_wrapped, font=bf, fill=body_color, spacing=14)
    if note:
        d.rounded_rectangle((70, H - 250, W - 70, H - 130), radius=28, fill=(255, 255, 255), outline=accent, width=3)
        nf, note_wrapped = fit_text(d, note, W - 200, 30, 24, True)
        d.multiline_text((100, H - 220), note_wrapped, font=nf, fill=fg, spacing=8)
    footer(d, source, number, footer_color)
    return canvas


def comment_slide(title: str, comments: list[dict], source: str, number: str,
                  bg=(25, 25, 29), accent=(255, 79, 68)) -> Image.Image:
    canvas = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(canvas)
    d.text((66, 72), "실제 댓글 · 계정 비식별", font=font(27, True), fill=accent)
    hf, wrapped = fit_text(d, title, W - 132, 58, 42, True)
    d.multiline_text((66, 150), wrapped, font=hf, fill="white", spacing=12)
    y = 350
    for item in comments:
        text = item["text"]
        likes = item.get("likes")
        cf, cw = fit_text(d, text, W - 210, 32, 25)
        lines = cw.count("\n") + 1
        h = max(145, 70 + lines * (cf.size + 12))
        d.rounded_rectangle((66, y, W - 66, y + h), radius=28, fill=(250, 250, 250))
        d.ellipse((96, y + 34, 142, y + 80), fill=accent)
        d.multiline_text((168, y + 30), cw, font=cf, fill=(35, 35, 40), spacing=10)
        if likes is not None:
            d.text((W - 180, y + h - 42), f"공감 {likes}", font=font(22, True), fill=accent)
        y += h + 28
    footer(d, source, number)
    return canvas


def screenshot_slide(image: Image.Image, eyebrow: str, headline: str, source: str, number: str, accent=(243, 70, 65)):
    canvas = Image.new("RGB", (W, H), (20, 22, 28))
    d = ImageDraw.Draw(canvas)
    d.text((64, 60), eyebrow, font=font(26, True), fill=accent)
    hf, wrapped = fit_text(d, headline, W - 128, 52, 38, True)
    d.multiline_text((64, 118), wrapped, font=hf, fill="white", spacing=10)
    frame = ImageOps.contain(image.convert("RGB"), (760, 920), Image.Resampling.LANCZOS)
    x, y = (W - frame.width) // 2, 305
    shadow = Image.new("RGBA", (frame.width + 40, frame.height + 40), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((20, 20, frame.width + 20, frame.height + 20), radius=28, fill=(0, 0, 0, 180))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    canvas.paste(shadow, (x - 20, y - 20), shadow)
    canvas.paste(frame, (x, y))
    footer(d, source, number)
    return canvas


def save_topic(slug: str, meta: dict, slides: list[Image.Image]):
    folder = ROOT / slug
    folder.mkdir(parents=True, exist_ok=True)
    for i, slide in enumerate(slides, 1):
        slide.save(folder / f"slide_{i:02d}.png", quality=95)
    thumbs = []
    for slide in slides:
        t = slide.copy(); t.thumbnail((270, 338), Image.Resampling.LANCZOS); thumbs.append(t)
    cols = 4; rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 290 + 40, rows * 370 + 60), (238, 238, 240))
    for i, t in enumerate(thumbs):
        sheet.paste(t, (20 + (i % cols) * 290, 20 + (i // cols) * 370))
    sheet.save(folder / "contact_sheet.png")
    (folder / "plan.json").write_text(json.dumps(meta["plan"], ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "manifest.json").write_text(json.dumps(meta["manifest"], ensure_ascii=False, indent=2), encoding="utf-8")


def build():
    meal_sheet = Image.open(ASSETS / "meal_kit_story_sheet.png")
    dating_sheet = Image.open(ASSETS / "dating_warning_sheet.png")
    app_shot = Image.open(ASSETS / "hospital_app_source.jpg")
    source_story = "출처: 네이트판 원문 · AI 재구성"
    source_comment = "출처: 네이트판 공개 댓글 · 2026.07.16 수집"

    meal_slides = [
        image_slide(panel(meal_sheet, 1), "가족 갈등 실화", "냉장고 열 때마다\n며느리 점수 매기는 시어머니", "몇 년째 반복된 밀키트 잔소리. 문제는 음식이 아니라 경계였다.", source_story, "1 / 8", reconstruction=True),
        image_slide(panel(meal_sheet, 0), "장면 01", "둘 다 지쳐서\n밀키트를 먹기 시작했다", "교대근무 남편과 맞벌이. 집에서 요리할 여유가 없었다는 작성자.", source_story, "2 / 8", reconstruction=True),
        image_slide(panel(meal_sheet, 1), "장면 02", "시어머니는 올 때마다\n냉장고부터 열었다", "“요즘 젊은 사람들은 밥을 안 해먹나 봐.” 한 번이 아니라 매 방문마다였다.", source_story, "3 / 8", reconstruction=True),
        image_slide(panel(meal_sheet, 2), "장면 03", "명절엔 시아버지 앞에서\n‘이 집은 밀키트만 먹는다’", "남편도 듣고 있었지만 그 자리에서 아무 말이 없었다고 했다.", source_story, "4 / 8", reconstruction=True),
        image_slide(panel(meal_sheet, 3), "장면 04", "방문 전 밀키트를\n숨길 생각까지 했다", "지금은 집밥을 더 자주 해도 냉장고 검사는 그대로였다.", source_story, "5 / 8", reconstruction=True),
        text_slide("남편의 한마디", "“우리 엄마 원래 그래.\n그냥 흘려들어.”", "몇 년째 쌓인 말을 ‘원래 그런 사람’으로 끝내버린 남편. 작성자가 가장 답답했던 지점이다.", source_story, "6 / 8", note="사연은 단일 커뮤니티 원문이며 독립 검증되지 않음"),
        comment_slide("댓글도 ‘경계 침범’과 ‘작성자 책임’으로 갈렸다", [
            {"text": "도대체 시어머니가 자식집에 왜 그리 들락날락하고 냉장고 체크까지 하는지. 시어머니 처신이 진짜 별로다", "likes": 40},
            {"text": "결론은 애도 없이 집에서 놀고 있는데 여전히 밀키트 시키니까 그러지", "likes": 20},
        ], source_comment, "7 / 8"),
        text_slide("당신이라면", "남편아, 밥보다 먼저\n할 말 없냐?", "밀키트가 문제였을까. 매번 냉장고를 검사하는 사람과 침묵한 사람 중 누가 먼저 선을 그어야 했을까.", source_story, "8 / 8", bg=(32, 29, 31), fg=(255, 255, 255), accent=(248, 76, 67)),
    ]
    meal_plan = {"account":"B","category":"relationship_real_story","topic":"시어머니 밀키트 잔소리","slide_count":8,"review_only":True,"slides":[{"slide":i+1,"media_type":"illustration" if i < 5 else "editorial" if i != 6 else "screenshot","role":r} for i,r in enumerate(["hook","setup","boundary","escalation","emotional_cost","partner_response","actual_reactions","human_cta"])]}
    meal_manifest = {"source_url":"https://pann.nate.com/talk/375519930","source_type":"community_single_source","actual_comments_used":True,"generated_media":"2D AI reconstruction clearly labeled","rights_status":"review_only_generated_and_public_comment_excerpt","publishing_ready":False,"gaps":["single community account","no independent verification","generated reconstruction needs owner approval"]}
    save_topic("relationship_real_story", {"plan":meal_plan,"manifest":meal_manifest}, meal_slides)

    issue_slides = [
        screenshot_slide(app_shot, "커뮤니티 이슈", "굳이?\n이게 계획적이 아니고?", "출처: 네이트판 원문 캡처", "1 / 7"),
        screenshot_slide(app_shot, "확인된 화면", "생년월일 예시에\n‘2014년 4월 16일’", "출처: 네이트판 원문 캡처", "2 / 7"),
        text_slide("왜 시선이 멈췄나", "무수한 날짜 중\n세월호 참사 당일", "원문 게시자는 병원 앱의 가족 환자 조회 화면에서 해당 날짜가 예시로 쓰였다고 제시했다.", "출처: 네이트판 원문", "3 / 7", note="화면 캡처 외 운영 주체·작성 경위는 독립 확인되지 않음"),
        text_slide("확인과 추정 분리", "화면은 보인다.\n‘의도’는 아직 모른다.", "의도적 선택인지, 템플릿 실수인지, 누가 작성했는지는 현재 자료만으로 확정할 수 없다.", "출처: 수집 데이터 검증 상태", "4 / 7", bg=(236, 241, 246), fg=(22, 31, 44), accent=(43, 102, 176)),
        comment_slide("공개 댓글의 첫 반응", [
            {"text":"보통 1월 1일로 하지 않나?"},
            {"text":"왜 하필;"},
        ], "출처: 네이트판 공개 댓글 · 2026.07.16 수집", "5 / 7"),
        text_slide("게시 전 필요한 것", "병원 측 설명과\n화면의 현재 상태 확인", "화면이 수정됐는지, 공식 해명이 있는지 확인하기 전에는 ‘계획적’이라고 단정해선 안 된다.", "내부 검토 기준", "6 / 7", note="현재 상태: NEEDS_EVIDENCE · 발행 불가"),
        text_slide("한 줄", "이 날짜를 넣은 이유,\n설명부터 해야 하지 않나.", "실수라면 바로잡고, 이유가 있다면 공개하면 된다. 지금 필요한 건 추측보다 설명이다.", "내부 검토용 시안", "7 / 7", bg=(24, 25, 31), fg=(255, 255, 255), accent=(245, 72, 66)),
    ]
    issue_plan = {"account":"B","category":"community_issue","topic":"병원 앱 생년월일 예시 논란","slide_count":7,"review_only":True,"slides":[{"slide":i+1,"media_type":"screenshot" if i < 2 else "editorial","role":r} for i,r in enumerate(["hook","evidence","why_attention","fact_inference_split","actual_reactions","verification_gap","editorial_close"])]}
    issue_manifest = {"source_url":"https://pann.nate.com/talk/375519754","source_type":"community_single_source","actual_comments_used":True,"source_image":"original post screenshot","rights_status":"unknown_review_only","publishing_ready":False,"gaps":["source timestamp missing in collection","app operator not independently verified","intent unverified","official response not collected"]}
    save_topic("community_issue", {"plan":issue_plan,"manifest":issue_manifest}, issue_slides)

    dating_slides = [
        image_slide(panel(dating_sheet, 0), "데이트앱 경고 썰", "얼굴도 못 봤는데,\n헉", "대화만 하던 남자가 털어놓은 이야기에 작성자는 바로 차단했다.", "출처: 네이트판 원문 · AI 재구성", "1 / 8", accent=(236, 40, 78), reconstruction=True),
        image_slide(panel(dating_sheet, 0), "장면 01", "지역이 멀어\n아직 만난 적도 없었다", "서로 호감도 없었고 메시지만 주고받았다는 작성자.", "출처: 네이트판 원문 · AI 재구성", "2 / 8", accent=(236, 40, 78), reconstruction=True),
        image_slide(panel(dating_sheet, 1), "장면 02", "그런데 그는\n‘여러 여성을 만난다’고 말했다", "파트너가 여러 명이라는 말까지 했다고 작성자는 주장했다.", "출처: 네이트판 원문 · 작성자 주장", "3 / 8", accent=(236, 40, 78), reconstruction=True),
        image_slide(panel(dating_sheet, 2), "장면 03", "건강 문제와 과거 일까지\n갑자기 꺼냈다", "민감한 내용은 단일 작성자의 주장으로, 사실 확인이 되지 않았다.", "출처: 네이트판 원문 · 작성자 주장", "4 / 8", accent=(236, 40, 78), reconstruction=True),
        text_slide("여기서 중요한 것", "순한 인상도, 직업도\n안전 확인이 아니다", "외모나 프로필보다 만남 전 경계 설정, 건강·신원 확인, 불편한 신호에서 대화를 끝낼 권리가 중요하다.", "편집자 안전 메모", "5 / 8", bg=(224, 232, 241), fg=(20, 30, 45), accent=(236, 40, 78)),
        image_slide(panel(dating_sheet, 3), "장면 04", "작성자는\n그 대화 뒤 바로 차단했다", "직접 만나지 않았기에 더 큰 피해로 이어지기 전 멈출 수 있었다.", "출처: 네이트판 원문 · AI 재구성", "6 / 8", accent=(236, 40, 78), reconstruction=True),
        comment_slide("댓글은 앱 이용자 자체를 비난했다", [
            {"text":"애초에 어플로 남자를 왜만나 .. 이 자존감없는것들아"},
        ], "출처: 네이트판 공개 댓글 · 2026.07.16 수집", "7 / 8", bg=(18, 24, 35), accent=(236, 40, 78)),
        text_slide("당신이라면", "얼굴도 못 봤는데\n여기서 끝. 차단 맞지?", "위험 신호를 설명하려 애쓰기보다, 불편하면 바로 나오는 선택도 충분하다.", "내부 검토용 시안", "8 / 8", bg=(16, 20, 31), fg=(255, 255, 255), accent=(236, 40, 78)),
    ]
    dating_plan = {"account":"B","category":"dating_dopamine","topic":"데이트앱 만남 전 위험 신호","slide_count":8,"review_only":True,"slides":[{"slide":i+1,"media_type":"illustration" if i in [0,1,2,3,5] else "editorial" if i != 6 else "screenshot","role":r} for i,r in enumerate(["emotion_hook","setup","escalation","shock","safety_context","decision","actual_reaction","low_friction_cta"])]}
    dating_manifest = {"source_url":"https://pann.nate.com/talk/375519792","source_type":"community_single_source","actual_comments_used":True,"generated_media":"2D AI reconstruction clearly labeled","privacy_actions":["job and detailed identifying clues omitted","no handles displayed"],"rights_status":"review_only_generated_and_public_comment_excerpt","publishing_ready":False,"gaps":["single author claim","sensitive health and reproductive claims unverified","source timestamp missing"]}
    save_topic("dating_dopamine", {"plan":dating_plan,"manifest":dating_manifest}, dating_slides)

    cards = [
        ("relationship_real_story", "관계·가족 실화", "8장 · 2D 재구성 + 실제 댓글"),
        ("community_issue", "커뮤니티 이슈", "7장 · 실제 캡처 + 검증 경계"),
        ("dating_dopamine", "데이트·도파민", "8장 · 감정 훅 + 안전 맥락"),
    ]
    blocks = "".join(f'<article><a href="{slug}/contact_sheet.png"><img src="{slug}/contact_sheet.png"></a><h2>{title}</h2><p>{desc}</p><a class="open" href="{slug}/slide_01.png">첫 장 열기</a></article>' for slug,title,desc in cards)
    html = f'''<!doctype html><html lang="ko"><meta charset="utf-8"><title>Account B 카드뉴스 검토</title><style>body{{margin:0;background:#111318;color:#f5f5f5;font-family:Malgun Gothic,sans-serif}}header{{padding:52px 5vw 24px}}h1{{font-size:44px;margin:0 0 10px}}header p{{color:#aeb4c0}}main{{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:30px;padding:24px 5vw 70px}}article{{background:#1d2028;border-radius:24px;padding:20px;box-shadow:0 16px 50px #0008}}img{{width:100%;border-radius:14px}}h2{{font-size:28px;margin-bottom:8px}}p{{color:#c4c9d2}}.open{{display:inline-block;background:#ff4f4a;color:white;text-decoration:none;padding:12px 18px;border-radius:999px;font-weight:700}}</style><header><h1>ACCOUNT B · 이슈 / 썰 / 관계</h1><p>2026-07-17 내부 데스크 검토용 · 게시 불가 · 각 카테고리 문법을 다르게 제작</p></header><main>{blocks}</main></html>'''
    (ROOT / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    build()
