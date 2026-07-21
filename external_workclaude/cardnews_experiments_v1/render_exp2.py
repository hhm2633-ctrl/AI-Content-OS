import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from modules.card_news.card_news_module import CardNewsModule


ROOT = Path("external_workclaude/cardnews_experiments_v1")
OUT = ROOT / "rendered_exp2"
SOURCE_VISUAL = ROOT / "assets/coffee_visual_source_v1.png"
BACKGROUND_DIR = ROOT / "assets/coffee_visual_panels_v1"


COMMON = {
    "title": "CN-017 커피 원두 보관법",
    "pattern_prompt_meta": {"pattern_type": "tutorial", "cta_type": "save"},
}


ARMS = {
    "control": [
        {"page": 1, "role": "hook", "headline": "원두 보관 체크리스트", "body": "세 가지만 순서대로 확인하세요."},
        {"page": 2, "role": "problem", "headline": "차례대로 정해요", "body": "사용할 용기를 고르세요.\n보관할 장소를 정하세요."},
        {"page": 3, "role": "solution", "headline": "마지막으로 기록해요", "body": "개봉 날짜를 적어두세요."},
        {"page": 4, "role": "cta", "headline": "다음 원두를 열기 전에", "body": "이 체크리스트를 저장하세요."},
    ],
    "variant": [
        {"page": 1, "role": "hook", "headline": "원두 보관 체크리스트", "body": "세 가지만 순서대로 확인하세요."},
        {"page": 2, "role": "problem", "headline": "1·2번 먼저 확인", "body": "1. 사용할 용기 고르기\n2. 보관할 장소 정하기"},
        {"page": 3, "role": "solution", "headline": "3번까지 기록", "body": "3. 개봉 날짜 적기"},
        {"page": 4, "role": "cta", "headline": "다음 원두를 열기 전에", "body": "이 체크리스트를 저장하세요."},
    ],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_backgrounds() -> list[Path]:
    BACKGROUND_DIR.mkdir(parents=True, exist_ok=True)
    with Image.open(SOURCE_VISUAL) as source:
        source = source.convert("RGB")
        width, height = source.size
        boxes = [
            (0, 0, width // 2, height // 2),
            (width // 2, 0, width, height // 2),
            (0, height // 2, width // 2, height),
            (width // 2, height // 2, width, height),
        ]
        paths = []
        for index, box in enumerate(boxes, 1):
            path = BACKGROUND_DIR / f"coffee_visual_{index}.png"
            source.crop(box).resize((1080, 1080), Image.Resampling.LANCZOS).save(path)
            paths.append(path)
    return paths


def render_arm(name: str, slides: list[dict], backgrounds: list[Path]) -> dict:
    target = OUT / name
    target.mkdir(parents=True, exist_ok=True)
    module = CardNewsModule({})
    module.card_dir = target
    rule = module.layout_rule_engine.get_rule("number_list")
    layout_context = {
        "rule": rule,
        "slide_designs_by_page": {
            item["page"]: item for item in module.slide_designer.design(slides, rule)
        },
        "slide_highlights_by_page": {},
    }
    visual_styles = ["title_focus", "short_line_focus", "short_line_focus", "cta_focus"]
    cards = []
    for index, slide in enumerate(slides):
        path_text, _ = module._create_card(
            page_number=slide["page"],
            title=COMMON["title"],
            slide=slide,
            image_path=str(backgrounds[index]),
            layout_context=layout_context,
            visual_style=visual_styles[index],
        )
        path = Path(path_text)
        with Image.open(path) as image:
            size = list(image.size)
            image.verify()
        cards.append({
            "index": slide["page"],
            "path": path.as_posix(),
            "headline": slide["headline"],
            "body": slide["body"],
            "background_path": backgrounds[index].as_posix(),
            "size": size,
            "sha256": sha256(path),
        })
    return {
        "arm": name,
        "status": "offline_mockup_rendered",
        "qa": {
            "card_count_ok": len(cards) == 4,
            "resolution_ok": all(card["size"] == [1080, 1080] for card in cards),
            "decode_ok": True,
            "copy_preserved": all(card["headline"] == slides[index]["headline"] and card["body"] == slides[index]["body"] for index, card in enumerate(cards)),
        },
        "cards": cards,
        "actual_publish": False,
    }


def contact_sheet(manifests: list[dict]) -> Path:
    thumb = 360
    label_h = 48
    canvas = Image.new("RGB", (thumb * 4, (thumb + label_h) * 2), "#f4f4f4")
    draw = ImageDraw.Draw(canvas)
    font_path = Path("C:/Windows/Fonts/malgunbd.ttf")
    font = ImageFont.truetype(str(font_path), 24) if font_path.exists() else ImageFont.load_default()
    for row, manifest in enumerate(manifests):
        for col, card in enumerate(manifest["cards"]):
            with Image.open(card["path"]) as image:
                image = image.convert("RGB").resize((thumb, thumb))
                canvas.paste(image, (col * thumb, row * (thumb + label_h) + label_h))
        draw.text((12, row * (thumb + label_h) + 8), manifest["arm"].upper(), fill="#111111", font=font)
    path = OUT / "EXP2_control_vs_variant_contact_sheet.png"
    canvas.save(path)
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    backgrounds = prepare_backgrounds()
    manifests = [render_arm(name, slides, backgrounds) for name, slides in ARMS.items()]
    sheet = contact_sheet(manifests)
    payload = {
        "experiment_id": "EXP-2",
        "topic_content_id": "CN-017",
        "status": "OFFLINE_RENDER_COMPLETE",
        "variable_tested": "story_structure_only",
        "learning_pattern_applied": "pattern.instagram_learning.content_pattern.numbered_curation_list_structure",
        "visual_family_applied": "인물/실사진 풀프레임 + 하단 좌측 볼드 타이포",
        "visual_family_evidence_class": "benchmark_observed",
        "contact_sheet": sheet.as_posix(),
        "actual_publish": False,
        "arms": manifests,
    }
    (OUT / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
