"""Render controller-authorized CardNews fragments into review-only packages.

This command is local-only.  It never posts, issues affiliate links, resumes an
automation, or changes Git state.  Rendering is not upload approval: every
output remains pending independent visual QA and owner review.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import shutil
import urllib.request
from urllib.parse import urljoin
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from modules.card_news.production_controller import (
    BATCH_AUTHORIZED,
    REPRESENTATIVE_AUTHORIZED,
    ProductionControllerError,
    validate_state,
)


CANVAS = (1080, 1350)
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "artifacts" / "cardnews_preupload_2026-07-19" / "fragments"
DEFAULT_OUTPUT = Path("F:/AI-Content-OS-Data/card_news/2026-07-19/preupload")
LEGACY_RENDERER_DISABLED_REASON = (
    "legacy_preupload_pillow_renderer_disabled_use_production_renderer_adapter"
)
BRANDS = {
    "A": ("NOW BRIEF", "오늘의 뉴스", (230, 63, 68)),
    "B": ("DOPAMINE NOTE", "썰 · 연애 · 이슈", (240, 113, 137)),
    "C": ("STYLE FILE", "패션 · 뷰티", (101, 214, 145)),
}
PALETTES = {
    "A": ((16, 18, 22), (244, 239, 230), (230, 63, 68), (33, 35, 39)),
    "B": ((255, 245, 224), (255, 252, 244), (240, 113, 137), (47, 38, 41)),
    "C": ((233, 236, 229), (250, 249, 244), (101, 214, 145), (27, 30, 29)),
}


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    paths = [
        Path("C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for path in paths:
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _safe_name(value: Any) -> str:
    clean = re.sub(r"[^0-9A-Za-z._-]+", "-", _text(value)).strip("-.")
    return clean[:96] or "candidate"


def _wrap(draw: ImageDraw.ImageDraw, value: str, face: ImageFont.ImageFont, width: int) -> List[str]:
    lines: List[str] = []
    for paragraph in (value.splitlines() or [value]):
        if not paragraph.strip():
            continue
        current = ""
        for token in paragraph.split():
            candidate = token if not current else f"{current} {token}"
            if draw.textbbox((0, 0), candidate, font=face)[2] <= width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = token
        if current:
            lines.append(current)
    return lines


def _draw_lines(
    draw: ImageDraw.ImageDraw,
    value: str,
    face: ImageFont.ImageFont,
    xy: tuple[int, int],
    width: int,
    fill: tuple[int, int, int],
    max_lines: int,
    spacing: int,
) -> int:
    all_lines = _wrap(draw, value, face, width)
    lines = all_lines[:max_lines]
    if len(all_lines) > max_lines and lines:
        while lines[-1] and draw.textbbox((0, 0), lines[-1] + "…", font=face)[2] > width:
            lines[-1] = lines[-1][:-1]
        lines[-1] = lines[-1].rstrip() + "…"
    x, y = xy
    height = face.getbbox("가Ay")[3] - face.getbbox("가Ay")[1]
    for line in lines:
        draw.text((x, y), line, font=face, fill=fill)
        y += height + spacing
    return y


def _open_image(path: Any) -> Optional[Image.Image]:
    value = _text(path)
    if not value:
        return None
    candidate = Path(value)
    try:
        with Image.open(candidate) as source:
            image = source.convert("RGB")
            image.load()
        return image
    except (OSError, ValueError):
        return None


def _cover_crop(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_ratio = size[0] / size[1]
    source_ratio = image.width / max(image.height, 1)
    if source_ratio > target_ratio:
        width = int(image.height * target_ratio)
        left = (image.width - width) // 2
        image = image.crop((left, 0, left + width, image.height))
    else:
        height = int(image.width / target_ratio)
        top = (image.height - height) // 2
        image = image.crop((0, top, image.width, top + height))
    return image.resize(size, Image.Resampling.LANCZOS)


def _contain(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    copy = image.copy()
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    return copy


def _all_asset_paths(record: Mapping[str, Any]) -> List[str]:
    paths: List[str] = []

    def add(value: Any) -> None:
        if isinstance(value, str) and value.strip():
            suffix = Path(value.strip()).suffix.lower()
            if suffix in {".png", ".jpg", ".jpeg", ".webp"} and value.strip() not in paths:
                paths.append(value.strip())
        elif isinstance(value, Mapping):
            for key in ("screenshot_path", "local_path", "asset_path", "path", "packaged_file"):
                add(value.get(key))
            for nested in value.values():
                if isinstance(nested, (Mapping, list)):
                    add(nested)
        elif isinstance(value, list):
            for item in value:
                add(item)

    add(record.get("evidence"))
    add(record.get("real_comment_evidence"))
    add(record.get("media_assets"))
    add(record.get("official_media"))
    add(record.get("product_assets"))
    return paths


def _comment_paths(record: Mapping[str, Any]) -> List[str]:
    evidence = record.get("real_comment_evidence")
    selected = evidence.get("selected") if isinstance(evidence, Mapping) else []
    selected = selected if isinstance(selected, list) else []
    return [
        _text(item.get("screenshot_path"))
        for item in selected if isinstance(item, Mapping) and _text(item.get("screenshot_path"))
    ]


def _resolve_slide_asset(
    record: Mapping[str, Any], slide: Mapping[str, Any], index: int, remote_map: Mapping[str, str]
) -> Optional[str]:
    for key in ("screenshot_path", "local_path", "asset_path", "image_path"):
        if _text(slide.get(key)):
            return _text(slide.get(key))
    role = _text(slide.get("role")).lower()
    media_note = _text(slide.get("media"))
    media = slide.get("media") if isinstance(slide.get("media"), Mapping) else {}
    asset_id = _text(media.get("asset_id"))
    if asset_id and remote_map.get(asset_id):
        return remote_map[asset_id]
    media_url = _text(slide.get("media_url") or media.get("url"))
    if media_url and remote_map.get(media_url):
        return remote_map[media_url]
    comments = _comment_paths(record)
    if "comment" in role or "댓글" in media_note or "comment_" in media_note.lower():
        for path in comments:
            if Path(path).name in media_note:
                return path
        if comments:
            comment_index = sum(
                1 for item in record.get("slides", [])[: max(index - 1, 0)]
                if isinstance(item, Mapping) and "comment" in _text(item.get("role")).lower()
            )
            return comments[min(comment_index, len(comments) - 1)]
    evidence = record.get("evidence") if isinstance(record.get("evidence"), Mapping) else {}
    if _text(evidence.get("source_id")) == "fmkorea":
        scene_paths = [remote_map[key] for key in sorted(remote_map) if key.startswith("fmkorea_scene_")]
        if scene_paths:
            return scene_paths[min(index - 1, len(scene_paths) - 1)]
    if index == 1 and _text(evidence.get("source_screenshot_path")):
        return _text(evidence.get("source_screenshot_path"))
    assets = _all_asset_paths(record)
    non_comments = [path for path in assets if "comment_" not in Path(path).name]
    return non_comments[(index - 1) % len(non_comments)] if non_comments else None


def _editorial_background(account: str, role: str, index: int) -> Image.Image:
    bg, _, accent, ink = PALETTES[account]
    image = Image.new("RGB", CANVAS, bg)
    draw = ImageDraw.Draw(image, "RGBA")
    if account == "A":
        mode = index % 3
        if mode == 0:
            for row, width in enumerate((720, 520, 830, 390)):
                y = 130 + row * 118
                draw.rounded_rectangle((88, y, 88 + width, y + 64), radius=18, fill=(*accent, 72 + row * 18))
        elif mode == 1:
            draw.rounded_rectangle((90, 115, 485, 610), radius=34, outline=(*accent, 140), width=7)
            draw.rounded_rectangle((595, 115, 990, 610), radius=34, fill=(*accent, 46))
            draw.line((540, 150, 540, 590), fill=(*accent, 200), width=8)
        else:
            for offset in range(-250, 1350, 170):
                draw.line((offset, 60, offset + 520, 780), fill=(*accent, 58), width=6)
            draw.ellipse((650, 90, 1050, 490), outline=(*accent, 150), width=16)
        draw.text((74, 145), f"{index:02d}", font=_font(190, True), fill=(*accent, 115))
    elif account == "B":
        draw.rounded_rectangle((76, 96, 1004, 650), radius=82, fill=(255, 255, 255, 205))
        draw.polygon([(838, 610), (978, 720), (915, 574)], fill=(255, 255, 255, 205))
        mode = index % 4
        if mode == 0:
            draw.text((150, 155), "?", font=_font(310, True), fill=(*accent, 210))
            draw.ellipse((580, 210, 770, 400), fill=(255, 210, 121, 180))
            draw.ellipse((735, 310, 925, 500), fill=(*accent, 125))
        elif mode == 1:
            draw.ellipse((145, 190, 325, 370), fill=(*accent, 160))
            draw.ellipse((745, 190, 925, 370), fill=(104, 160, 255, 135))
            draw.line((325, 280, 745, 280), fill=(*ink, 100), width=8)
            draw.arc((390, 190, 680, 500), 15, 165, fill=(*accent, 220), width=16)
        elif mode == 2:
            for row in range(4):
                y = 170 + row * 98
                draw.rounded_rectangle((150, y, 215, y + 65), radius=16, outline=(*accent, 220), width=6)
                draw.line((260, y + 32, 850 - row * 55, y + 32), fill=(*ink, 85), width=12)
        else:
            draw.text((135, 125), "“", font=_font(330, True), fill=(*accent, 175))
            draw.line((385, 285, 885, 285), fill=(*ink, 90), width=15)
            draw.line((385, 370, 760, 370), fill=(*ink, 65), width=15)
        for x, y, size in ((820, 110, 96), (920, 245, 52), (105, 555, 72)):
            draw.ellipse((x, y, x + size, y + size), fill=(*accent, 76))
    else:
        draw.rectangle((62, 72, 1018, 690), outline=(*ink, 55), width=2)
        draw.ellipse((610, 90, 1050, 530), fill=(*accent, 72))
        draw.rectangle((78, 515, 745, 705), fill=(255, 255, 255, 55))
        draw.text((88, 132), "EDITORIAL", font=_font(38, True), fill=(*ink, 155))
    return image


def _render_slide(
    account: str,
    record: Mapping[str, Any],
    slide: Mapping[str, Any],
    index: int,
    total: int,
    remote_map: Mapping[str, str],
) -> Image.Image:
    bg, panel, accent, ink = PALETTES[account]
    role = _text(slide.get("role") or "story")
    asset_path = _resolve_slide_asset(record, slide, index, remote_map)
    asset = _open_image(asset_path)
    is_comment = "comment" in role.lower() or (asset_path and "comment_" in Path(asset_path).name)
    if asset is None:
        image = _editorial_background(account, role, index)
    elif is_comment:
        image = _editorial_background(account, role, index)
        card = _contain(asset, (900, 230))
        shadow = Image.new("RGBA", (card.width + 36, card.height + 36), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle((18, 18, card.width + 18, card.height + 18), radius=26, fill=(0, 0, 0, 45))
        x = (CANVAS[0] - card.width) // 2
        y = 505
        image.paste(shadow, (x - 18, y - 18), shadow)
        image.paste(card, (x, y))
        selected = record.get("real_comment_evidence", {}).get("selected", []) if isinstance(record.get("real_comment_evidence"), Mapping) else []
        comment_text = ""
        for item in selected if isinstance(selected, list) else []:
            if isinstance(item, Mapping) and Path(_text(item.get("screenshot_path"))).name == Path(_text(asset_path)).name:
                comment_text = _text(item.get("text"))
                break
        if comment_text:
            quote_draw = ImageDraw.Draw(image, "RGBA")
            quote_draw.rounded_rectangle((105, 116, 975, 470), radius=42, fill=(255, 255, 255, 238))
            quote_draw.text((145, 145), "실제 댓글 · 신원 가림", font=_font(24, True), fill=accent)
            _draw_lines(quote_draw, f"“{comment_text}”", _font(36, True), (145, 205), 790, ink, 5, 9)
    else:
        image = _cover_crop(asset, (CANVAS[0], 820))
        image = ImageEnhance.Contrast(image).enhance(1.04)
        canvas = Image.new("RGB", CANVAS, bg)
        canvas.paste(image, (0, 0))
        fade = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
        fd = ImageDraw.Draw(fade)
        for y in range(540, 840):
            alpha = int(210 * ((y - 540) / 300))
            fd.rectangle((0, y, 1080, y + 1), fill=(0, 0, 0, alpha))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), fade).convert("RGB")
        image = canvas

    draw = ImageDraw.Draw(image, "RGBA")
    brand, category_line, _ = BRANDS[account]
    top_ink = (250, 248, 242) if asset is not None and not is_comment else ink
    draw.rounded_rectangle((58, 48, 390, 102), radius=24, fill=(*accent, 235))
    draw.text((82, 60), brand, font=_font(24, True), fill=(15, 16, 18))
    draw.text((840, 60), f"{index:02d} / {total:02d}", font=_font(25, True), fill=top_ink)

    panel_top = 790
    draw.rounded_rectangle((42, panel_top, 1038, 1307), radius=42, fill=(*panel, 250))
    draw.rectangle((80, panel_top + 62, 92, panel_top + 155), fill=(*accent, 255))
    draw.text((122, panel_top + 58), category_line, font=_font(26, True), fill=accent)
    headline = _text(slide.get("headline"))
    body = _text(slide.get("body"))
    title_size = 62 if len(headline.replace("\n", "")) <= 28 else 54
    y = _draw_lines(draw, headline, _font(title_size, True), (122, panel_top + 105), 830, ink, 3, 10)
    _draw_lines(draw, body, _font(30), (122, min(y + 24, 1124)), 830, (75, 70, 69), 3, 10)

    credit = ""
    evidence = record.get("evidence") if isinstance(record.get("evidence"), Mapping) else {}
    source_id = _text(evidence.get("source_id") or evidence.get("publisher"))
    if source_id:
        credit = {"nate_pann": "네이트판 공개 원문·댓글", "fmkorea": "FM코리아 공개 원문·댓글"}.get(source_id, source_id)
    elif account == "C":
        credit = _text(slide.get("source_credit") or "공식·에디토리얼 자료")
    elif account == "A":
        media = slide.get("media") if isinstance(slide.get("media"), Mapping) else {}
        credit = _text(slide.get("source_credit") or media.get("credit") or "본문 참고·자체 편집")
    draw.line((80, 1260, 1000, 1260), fill=(*ink, 60), width=2)
    draw.text((82, 1274), credit[:46], font=_font(20), fill=(105, 101, 98))
    return image.convert("RGB")


def _contact_sheet(paths: Sequence[Path], target: Path) -> None:
    thumb_w, thumb_h = 216, 270
    cols = 4
    rows = math.ceil(len(paths) / cols)
    sheet = Image.new("RGB", (cols * thumb_w + (cols + 1) * 20, rows * thumb_h + (rows + 1) * 20), (18, 19, 21))
    for index, path in enumerate(paths):
        with Image.open(path) as raw:
            thumb = raw.convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = 20 + (index % cols) * (thumb_w + 20)
        y = 20 + (index // cols) * (thumb_h + 20)
        sheet.paste(thumb, (x, y))
    sheet.save(target, optimize=True)


def _load_fragments(root: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for account in ("A", "B", "C"):
        path = root / f"account_{account}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        for raw in payload.get("records", []):
            if isinstance(raw, Mapping):
                record = dict(raw)
                record["account"] = account
                records.append(record)
    return records


def _extension_from_url(url: str, content_type: str = "") -> str:
    suffix = Path(url.split("?", 1)[0]).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    return {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(content_type, ".jpg")


def _download_image(url: str, target_stem: Path) -> Optional[Path]:
    for existing in target_stem.parent.glob(f"{target_stem.name}.*") if target_stem.parent.exists() else []:
        if _open_image(existing) is not None:
            return existing
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AI-Content-OS/1.0"})
        with urllib.request.urlopen(request, timeout=20) as response:
            content_type = _text(response.headers.get("Content-Type")).split(";", 1)[0].lower()
            if content_type and not content_type.startswith("image/"):
                return None
            payload = response.read(30 * 1024 * 1024 + 1)
        if not payload or len(payload) > 30 * 1024 * 1024:
            return None
        target = target_stem.with_suffix(_extension_from_url(url, content_type))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        with Image.open(target) as image:
            image.verify()
        return target
    except Exception:
        return None


def _capture_page(url: str, target: Path) -> Optional[Path]:
    if _open_image(target) is not None:
        return target
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            chrome = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
            kwargs: Dict[str, Any] = {"headless": True}
            if chrome.is_file():
                kwargs["executable_path"] = str(chrome)
            browser = playwright.chromium.launch(**kwargs)
            page = browser.new_page(viewport={"width": 1365, "height": 1800}, device_scale_factor=1)
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            # A bounded first-view capture is sufficient for the title/lead
            # evidence role and avoids pages with endless/lazy content turning
            # a manual-upload render into an unbounded full-page screenshot.
            page.screenshot(path=str(target), full_page=False, type="png", timeout=10000)
            browser.close()
        return target if target.is_file() else None
    except Exception:
        return None


def _prepare_remote_assets(record: Mapping[str, Any], root: Path) -> tuple[Dict[str, str], Dict[str, int]]:
    cache = root / "media_cache" / _safe_name(record.get("candidate_id"))
    mapping: Dict[str, str] = {}
    stats = {"downloaded": 0, "captured": 0, "failed": 0}

    evidence = record.get("evidence") if isinstance(record.get("evidence"), Mapping) else {}
    assets = evidence.get("media_assets") if isinstance(evidence.get("media_assets"), list) else []
    for raw in assets:
        if not isinstance(raw, Mapping):
            continue
        asset_id = _text(raw.get("asset_id"))
        url = _text(raw.get("url"))
        capture = _text(raw.get("capture_target"))
        stem = cache / (_safe_name(asset_id) or hashlib.sha1((url or capture).encode()).hexdigest()[:12])
        path = _download_image(url, stem) if url else None
        if path is None and capture:
            path = _capture_page(capture, stem.with_suffix(".png"))
            stats["captured" if path else "failed"] += 1
        elif path:
            stats["downloaded"] += 1
        elif url:
            stats["failed"] += 1
        if path:
            if asset_id:
                mapping[asset_id] = str(path)
            if url:
                mapping[url] = str(path)
            if capture:
                mapping[capture] = str(path)

    if _text(evidence.get("source_id")) == "fmkorea":
        raw_path = Path(_text(evidence.get("raw_html_path")))
        source_url = _text(evidence.get("source_url"))
        try:
            import lxml.html

            document = lxml.html.fromstring(raw_path.read_bytes())
            nodes = document.xpath("//*[contains(concat(' ', normalize-space(@class), ' '), ' xe_content ')]//img")
            urls: List[str] = []
            for node in nodes:
                value = _text(node.get("data-original") or node.get("data-src") or node.get("src"))
                if value:
                    value = urljoin(source_url, value)
                if value.startswith(("http://", "https://")) and value not in urls:
                    urls.append(value)
            for position, url in enumerate(urls[:8], start=1):
                path = _download_image(url, cache / f"fmkorea-scene-{position:02d}")
                stats["downloaded" if path else "failed"] += 1
                if path:
                    mapping[f"fmkorea_scene_{position:02d}"] = str(path)
        except Exception:
            stats["failed"] += 1

    for slide in record.get("slides", []):
        if not isinstance(slide, Mapping):
            continue
        url = _text(slide.get("media_url"))
        if not url or url in mapping or "brandconnect.naver.com" in url:
            continue
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
        path = _download_image(url, cache / f"remote-{digest}")
        stats["downloaded" if path else "failed"] += 1
        if path:
            mapping[url] = str(path)
    return mapping, stats


def _usable_slides(record: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    slides = [slide for slide in record.get("slides", []) if isinstance(slide, Mapping)]
    usable = []
    for slide in slides:
        status = _text(slide.get("asset_status"))
        url = _text(slide.get("media_url"))
        if status.startswith("requires_logged_in") and "brandconnect.naver.com" in url:
            continue
        usable.append(slide)
    return usable


def _effective_caption(record: Mapping[str, Any], slides: Sequence[Mapping[str, Any]]) -> str:
    caption = _text(record.get("feed_caption"))
    original_count = len([item for item in record.get("slides", []) if isinstance(item, Mapping)])
    if len(slides) == original_count:
        return caption
    lines = []
    for line in caption.splitlines():
        normalized = line.strip().lower()
        if "naver brand connect" in normalized or "네이버 쇼핑 커넥트" in normalized:
            continue
        if normalized.startswith("상품 정보:"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _write_gallery(output: Path, manifest: Mapping[str, Any]) -> None:
    cards = []
    for record in manifest["records"]:
        preview = Path(record["contact_sheet"]).relative_to(output).as_posix()
        caption = Path(record["caption_path"]).relative_to(output).as_posix()
        cards.append(
            f"<article><h2>{html.escape(record['title'])}</h2>"
            f"<p>{html.escape(record['account'])} · {record['slide_count']}장 · 댓글 {record['real_comment_count']}개 사용</p>"
            f"<img src='{html.escape(preview)}' alt='contact sheet'>"
            f"<p><a href='{html.escape(caption)}'>피드 본문 보기</a></p></article>"
        )
    page = """<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>CardNews Pre-upload</title>
<style>body{margin:0;background:#111318;color:#f4f1e9;font-family:Arial,'Malgun Gothic',sans-serif}header{padding:42px 5vw;border-bottom:1px solid #353840}main{padding:34px 5vw;display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:28px}article{background:#1b1e24;padding:22px;border-radius:22px}img{width:100%;border-radius:12px}h2{font-size:21px;line-height:1.4}p{color:#bfc2ca}a{color:#9febb9}</style></head><body><header><h1>2026-07-19 최종 업로드 직전 패키지</h1><p>실제 게시·링크 발급은 실행하지 않음</p></header><main>""" + "".join(cards) + "</main></body></html>"
    (output / "index.html").write_text(page, encoding="utf-8")


def _account_overviews(output: Path, records: Sequence[Mapping[str, Any]]) -> Dict[str, str]:
    results: Dict[str, str] = {}
    for account in ("A", "B", "C"):
        paths = [Path(item["contact_sheet"]) for item in records if item.get("account") == account and item.get("contact_sheet")]
        images: List[Image.Image] = []
        for path in paths:
            with Image.open(path) as raw:
                image = raw.convert("RGB")
                image.load()
            images.append(image)
        if not images:
            continue
        width = max(image.width for image in images)
        gap = 28
        canvas = Image.new("RGB", (width, sum(image.height for image in images) + gap * (len(images) - 1)), (15, 16, 19))
        y = 0
        for image in images:
            canvas.paste(image, ((width - image.width) // 2, y))
            y += image.height + gap
        target = output / f"account_{account}_overview.png"
        canvas.save(target, optimize=True)
        results[account] = str(target)
    return results


def _fragment_digest(input_root: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(input_root.glob("account_*.json"), key=lambda path: path.name.lower())
    if not files:
        return ""
    for path in files:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _authorized_records(
    records: Sequence[Mapping[str, Any]],
    authorization: Mapping[str, Any] | None,
    *,
    input_root: Path,
    output_root: Path,
) -> List[Dict[str, Any]]:
    if not isinstance(authorization, Mapping) or authorization.get("authorized") is not True:
        raise PermissionError("controller_render_authorization_required")
    if authorization.get("schema_version") != "cardnews_render_authorization_v1":
        raise PermissionError("invalid_render_authorization_schema")
    state_path = Path(_text(authorization.get("controller_state_path")))
    try:
        controller_state = json.loads(state_path.read_text(encoding="utf-8"))
        validate_state(controller_state)
    except (OSError, json.JSONDecodeError, ProductionControllerError) as exc:
        raise PermissionError("controller_state_invalid") from exc
    if _text(authorization.get("controller_state_hash")) != _text(controller_state.get("state_hash")):
        raise PermissionError("controller_state_hash_mismatch")
    if _text(authorization.get("controller_id")) != _text(controller_state.get("controller_id")):
        raise PermissionError("controller_id_mismatch")
    if _text(authorization.get("hard_rule_hash")) != _text(controller_state.get("hard_rule_hash")):
        raise PermissionError("controller_hard_rule_hash_mismatch")
    if _text(authorization.get("batch_hash")) != _text(controller_state.get("batch_hash")):
        raise PermissionError("controller_batch_hash_mismatch")
    expected_input = _text(authorization.get("input_sha256"))
    if not expected_input or expected_input != _fragment_digest(input_root):
        raise PermissionError("render_authorization_input_hash_mismatch")
    expected_output = _text(authorization.get("output_root"))
    if not expected_output or Path(expected_output).resolve() != output_root.resolve():
        raise PermissionError("render_authorization_output_root_mismatch")
    expires_at = _text(authorization.get("expires_at"))
    try:
        expiry = datetime.fromisoformat(expires_at)
    except ValueError as exc:
        raise PermissionError("render_authorization_expiry_required") from exc
    if expiry.tzinfo is None or expiry <= datetime.now().astimezone():
        raise PermissionError("render_authorization_expired")
    mode = _text(authorization.get("mode"))
    if mode not in {"representative", "batch"}:
        raise PermissionError("invalid_render_authorization_mode")
    allowed = {
        _text(value)
        for value in authorization.get("candidate_ids", [])
        if _text(value)
    }
    if not allowed:
        raise PermissionError("authorized_candidate_ids_required")
    expected_state = REPRESENTATIVE_AUTHORIZED if mode == "representative" else BATCH_AUTHORIZED
    if controller_state.get("state") != expected_state:
        raise PermissionError("controller_state_not_render_authorized")
    expected_candidates = (
        set(controller_state.get("representatives", {}).values())
        if mode == "representative"
        else set(controller_state.get("candidate_ids", []))
    )
    if allowed != expected_candidates:
        raise PermissionError("controller_candidate_scope_mismatch")
    selected = [dict(record) for record in records if _text(record.get("candidate_id")) in allowed]
    if { _text(record.get("candidate_id")) for record in selected } != allowed:
        raise PermissionError("authorized_candidate_not_found")
    if mode == "representative":
        per_account: Dict[str, int] = {}
        for record in selected:
            account = _text(record.get("account"))
            per_account[account] = per_account.get(account, 0) + 1
        if any(count > 1 for count in per_account.values()):
            raise PermissionError("representative_mode_allows_one_candidate_per_account")
    return selected


def _consume_authorization(output_root: Path, authorization: Mapping[str, Any]) -> Path:
    authorization_id = _safe_name(authorization.get("authorization_id"))
    if not _text(authorization.get("authorization_id")):
        raise PermissionError("render_authorization_id_required")
    receipt_dir = output_root.parent / ".controller_authorizations"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt = receipt_dir / f"{authorization_id}.consumed.json"
    payload = {
        "schema_version": "cardnews_render_authorization_consumption_v1",
        "authorization_id": _text(authorization.get("authorization_id")),
        "input_sha256": _text(authorization.get("input_sha256")),
        "output_root": str(output_root.resolve()),
        "consumed_at": datetime.now().astimezone().isoformat(),
    }
    try:
        with receipt.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
    except FileExistsError as exc:
        raise PermissionError("render_authorization_already_consumed") from exc
    return receipt


def render_batch(
    input_root: Path,
    output_root: Path,
    *,
    authorization: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    # This legacy Pillow path previously bypassed the production renderer contract.
    # Keep the callable for import compatibility, but fail before reading fragments,
    # validating/consuming an authorization, or creating any output directory.
    raise PermissionError(LEGACY_RENDERER_DISABLED_REASON)

    if not isinstance(authorization, Mapping) or authorization.get("authorized") is not True:
        raise PermissionError("controller_render_authorization_required")
    records = _load_fragments(input_root)
    records = _authorized_records(
        records,
        authorization,
        input_root=input_root,
        output_root=output_root,
    )
    _consume_authorization(output_root, authorization or {})
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_records: List[Dict[str, Any]] = []
    for record in records:
        slides = _usable_slides(record)
        status = _text(record.get("production_status"))
        if not slides or status.startswith("blocked"):
            manifest_records.append({
                "candidate_id": _text(record.get("candidate_id")), "account": record["account"],
                "title": _text(record.get("title")), "status": "blocked", "blocking_reasons": record.get("blockers", []),
                "slide_count": 0, "real_comment_count": 0, "outputs": [], "contact_sheet": "", "caption_path": "",
            })
            continue
        candidate_dir = output_root / f"account_{record['account']}" / _safe_name(record.get("candidate_id"))
        slide_dir = candidate_dir / "slides"
        slide_dir.mkdir(parents=True, exist_ok=True)
        outputs: List[Path] = []
        remote_map, asset_stats = _prepare_remote_assets(record, output_root)
        for index, slide in enumerate(slides, start=1):
            image = _render_slide(record["account"], record, slide, index, len(slides), remote_map)
            path = slide_dir / f"{index:02d}.png"
            image.save(path, optimize=True)
            outputs.append(path)
        sheet = candidate_dir / "contact_sheet.png"
        _contact_sheet(outputs, sheet)
        caption_path = candidate_dir / "feed_caption.txt"
        effective_caption = _effective_caption(record, slides)
        caption_path.write_text(effective_caption + "\n", encoding="utf-8")
        package_json = candidate_dir / "package.json"
        rendered_record = dict(record)
        rendered_record["rendered_slide_count"] = len(slides)
        rendered_record["rendered_feed_caption"] = effective_caption
        package_json.write_text(json.dumps(rendered_record, ensure_ascii=False, indent=2), encoding="utf-8")
        used_comments = sum(
            1
            for slide in slides
            if "comment" in _text(slide.get("role")).lower()
            or "댓글" in _text(slide.get("media"))
            or "comment_" in _text(slide.get("media")).lower()
        )
        manifest_records.append({
            "candidate_id": _text(record.get("candidate_id")), "account": record["account"],
            "title": _text(record.get("title")), "status": "render_completed_pending_visual_qa", "blocking_reasons": [],
            "slide_count": len(outputs), "real_comment_count": used_comments,
            "outputs": [str(path) for path in outputs], "contact_sheet": str(sheet), "caption_path": str(caption_path),
            "package_path": str(package_json),
            "asset_stats": asset_stats,
        })
    rendered = sum(item["status"] == "render_completed_pending_visual_qa" for item in manifest_records)
    manifest = {
        "schema_version": "cardnews_render_review_manifest_v2",
        "generated_at": datetime.now().astimezone().isoformat(),
        "date": "2026-07-19",
        "status": "rendered_pending_visual_qa" if rendered == len(manifest_records) and rendered else "partial",
        "record_count": len(manifest_records), "rendered_count": rendered,
        "ready_count": 0, "blocked_count": len(manifest_records) - rendered,
        "visual_qa_passed": False, "owner_review_ready": False,
        "authorization_id": _text(authorization.get("authorization_id")) if isinstance(authorization, Mapping) else "",
        "output_set_id": _text(authorization.get("authorization_id")) if isinstance(authorization, Mapping) else "",
        "controller_state_hash": _text(authorization.get("controller_state_hash")) if isinstance(authorization, Mapping) else "",
        "batch_hash": _text(authorization.get("batch_hash")) if isinstance(authorization, Mapping) else "",
        "hard_rule_hash": _text(authorization.get("hard_rule_hash")) if isinstance(authorization, Mapping) else "",
        "render_mode": _text(authorization.get("mode")) if isinstance(authorization, Mapping) else "",
        "upload_mode": "manual", "posted": False, "affiliate_links_issued": False, "git_executed": False,
        "records": manifest_records,
    }
    manifest["account_overviews"] = _account_overviews(output_root, manifest_records)
    (output_root / "manual_upload_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_gallery(output_root, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--authorization", type=Path, required=True)
    args = parser.parse_args()
    try:
        # Do not read the authorization file here. The disabled legacy entry must
        # fail before a token can be validated or consumed and before output exists.
        manifest = render_batch(args.input_root, args.output_root)
    except PermissionError as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({key: manifest[key] for key in ("status", "record_count", "rendered_count", "ready_count", "blocked_count")}, ensure_ascii=False))
    return 0 if manifest["rendered_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
