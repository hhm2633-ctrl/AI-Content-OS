"""Manual-upload publish package builder for category media packs.

Takes one reviewed topic input plus its category media pack result and emits a
manual-upload package: ordered slide files, ``caption.txt``, ``sources.txt``,
``preview.html`` (relative paths only), and a package-level ``manifest.json``.
It never calls Instagram/Meta APIs and never marks anything published; missing
caption/media/source input degrades to an honest blocked manifest instead of an
exception.
"""

from __future__ import annotations

import html
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.card_news.category_media_pack import (
    build_topic_slug,
    load_package_config,
)

VIDEO_EXTENSIONS = {".mp4"}


class CategoryPublishPackageBuilder:
    """Emit a manual-upload publish package for one reviewed topic."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, config_path: Optional[Path] = None):
        self.config_warnings: List[str] = []
        if config is not None:
            self.config = config
        else:
            self.config, self.config_warnings = load_package_config(config_path)

    def build(
        self,
        topic_input: Any,
        media_pack_result: Any,
        package_dir: Path,
    ) -> Dict[str, Any]:
        try:
            return self._build(topic_input, media_pack_result, Path(package_dir))
        except Exception as exc:  # never escape the builder
            manifest = self._base_manifest(topic_input, media_pack_result)
            manifest["blocking_reasons"].append(
                f"internal_error: publish package builder failed ({type(exc).__name__})"
            )
            manifest["status"] = "publish_package_blocked"
            manifest["publish_status"] = "blocked"
            manifest["fallback_used"] = True
            self._write_manifest(Path(package_dir), manifest)
            return manifest

    def _build(
        self, topic_input: Any, media_pack_result: Any, package_dir: Path
    ) -> Dict[str, Any]:
        manifest = self._base_manifest(topic_input, media_pack_result)
        blocking = manifest["blocking_reasons"]
        warnings = manifest["warnings"]

        if not isinstance(topic_input, dict):
            topic_input = {}
            blocking.append("input_invalid: reviewed topic input must be a JSON object")
        if not isinstance(media_pack_result, dict):
            media_pack_result = {}
            blocking.append("media_pack_missing: media pack result is unavailable")
        elif media_pack_result.get("status") != "media_pack_ready":
            blocking.extend(
                str(reason) for reason in media_pack_result.get("blocking_reasons", [])
            )
            if media_pack_result.get("status") != "media_pack_ready" and not blocking:
                blocking.append("media_pack_blocked: media pack did not become ready")

        category = manifest["category"].get("canonical_category")
        caption = topic_input.get("caption")
        caption = caption.strip() if isinstance(caption, str) else ""
        if not caption:
            blocking.append("caption_missing: reviewed input supplied no caption")
        else:
            marker = self._internal_marker(caption)
            if marker:
                blocking.append(
                    f"internal_review_marker_in_caption: public copy contains '{marker}'; "
                    "internal operations notes must stay out of the published package"
                )

        sources = self._normalize_sources(topic_input.get("sources"), warnings)
        news_categories = set(self.config.get("news_categories", []))
        if category in news_categories and not sources:
            blocking.append(
                "news_source_missing: news packages require the supplied source records"
            )

        slides = self._publishable_slides(media_pack_result)
        if not blocking and not slides:
            blocking.append("no_publishable_media: no packaged slide is available")

        if blocking:
            manifest["status"] = "publish_package_blocked"
            manifest["publish_status"] = "blocked"
            manifest["next_action"] = (
                "blocking_reasons를 해결한 뒤 패키지를 다시 생성한다; 게시물은 만들어지지 않았다"
            )
            manifest["fallback_used"] = True
            self._write_manifest(package_dir, manifest)
            return manifest

        publish_dir = package_dir / "publish_package"
        publish_dir.mkdir(parents=True, exist_ok=True)

        slide_records = self._copy_slides(slides, package_dir, publish_dir, blocking)
        if blocking:
            manifest["status"] = "publish_package_blocked"
            manifest["publish_status"] = "blocked"
            manifest["fallback_used"] = True
            self._write_manifest(package_dir, manifest)
            return manifest

        final_caption = self._final_caption(caption, category, sources, topic_input)
        (publish_dir / "caption.txt").write_text(final_caption + "\n", encoding="utf-8")
        (publish_dir / "sources.txt").write_text(
            self._sources_text(sources, category), encoding="utf-8"
        )
        (publish_dir / "preview.html").write_text(
            self._preview_html(manifest["title"], category, slide_records, final_caption),
            encoding="utf-8",
        )

        manifest.update({
            "status": "publish_package_ready",
            "publish_status": "manual_upload_pending",
            "next_action": "publish_package/의 슬라이드와 caption.txt로 운영자가 직접 수동 업로드한다",
            "caption_file": "publish_package/caption.txt",
            "sources_file": "publish_package/sources.txt",
            "preview_file": "publish_package/preview.html",
            "slides": slide_records,
            "slide_count": len(slide_records),
        })
        self._write_manifest(package_dir, manifest)
        return manifest

    def _base_manifest(self, topic_input: Any, media_pack_result: Any) -> Dict[str, Any]:
        topic = topic_input if isinstance(topic_input, dict) else {}
        pack = media_pack_result if isinstance(media_pack_result, dict) else {}
        category = pack.get("category")
        if not isinstance(category, dict):
            category = {
                "status": "blocked",
                "input_category": None,
                "canonical_category": None,
                "reason": "category_missing: media pack carried no category result",
            }
        return {
            "schema_version": "category_publish_package_v1",
            "status": "publish_package_blocked",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "topic_id": str(topic.get("topic_id", "")),
            "topic_slug": build_topic_slug(topic),
            "title": str(topic.get("title", "")),
            "category": category,
            "upload_mode": "manual",
            "published": False,
            "publish_status": "blocked",
            "next_action": "",
            "caption_file": None,
            "sources_file": None,
            "preview_file": None,
            "slides": [],
            "slide_count": 0,
            "media_pack": {
                "status": str(pack.get("status", "unavailable")),
                "counts": pack.get("counts", {}),
                "publishable_items": pack.get("publishable_items", 0),
                "download_mode": bool(pack.get("download_mode", False)),
                "manifest_file": "media_pack/media_pack.json",
            },
            "blocking_reasons": [],
            "warnings": list(self.config_warnings) + [
                str(item) for item in (pack.get("warnings") or []) if item
            ],
            "fallback_used": False,
        }

    def _internal_marker(self, caption: str) -> Optional[str]:
        for marker in self.config.get("internal_review_markers", []):
            if str(marker) and str(marker) in caption:
                return str(marker)
        return None

    def _normalize_sources(self, raw: Any, warnings: List[str]) -> List[Dict[str, str]]:
        sources: List[Dict[str, str]] = []
        if raw is None:
            return sources
        if not isinstance(raw, list):
            warnings.append("sources field is malformed and was ignored")
            return sources
        for position, entry in enumerate(raw, start=1):
            if isinstance(entry, str):
                entry = {"url": entry}
            if not isinstance(entry, dict):
                warnings.append(f"source record {position} is not an object and was skipped")
                continue
            record = {
                "publisher": str(entry.get("publisher", "")).strip(),
                "url": str(entry.get("url", "")).strip(),
                "title": str(entry.get("title", "")).strip(),
                "note": str(entry.get("note", "")).strip(),
            }
            if not record["publisher"] and not record["url"]:
                warnings.append(f"source record {position} has no publisher or URL and was skipped")
                continue
            sources.append(record)
        return sources

    def _publishable_slides(self, media_pack_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        items = media_pack_result.get("items")
        if not isinstance(items, list):
            return []
        slides = [
            item
            for item in items
            if isinstance(item, dict) and item.get("publishable") and item.get("packaged_file")
        ]
        slides.sort(key=lambda item: (item.get("order", 0), item.get("sequence", 0)))
        return slides

    def _copy_slides(
        self,
        slides: List[Dict[str, Any]],
        package_dir: Path,
        publish_dir: Path,
        blocking: List[str],
    ) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        for position, item in enumerate(slides, start=1):
            source = package_dir / str(item["packaged_file"])
            extension = source.suffix.lower()
            target = publish_dir / f"slide_{position:02d}{extension}"
            try:
                shutil.copy2(source, target)
            except OSError as exc:
                blocking.append(
                    f"slide_copy_failed: {item['packaged_file']} could not be staged "
                    f"({type(exc).__name__})"
                )
                continue
            records.append({
                "position": position,
                "file": f"publish_package/{target.name}",
                "media_type": item.get("media_type", ""),
                "slide_role": item.get("slide_role", ""),
                "origin": item.get("origin", ""),
                "asset_class": item.get("asset_class", ""),
                "source_url": item.get("source_url", ""),
                "publisher": item.get("publisher", ""),
                "brand": item.get("brand", ""),
                "media_pack_file": item.get("packaged_file", ""),
            })
        return records

    def _final_caption(
        self,
        caption: str,
        category: Optional[str],
        sources: List[Dict[str, str]],
        topic_input: Dict[str, Any],
    ) -> str:
        explicit_line = topic_input.get("caption_source_line")
        explicit_line = explicit_line.strip() if isinstance(explicit_line, str) else ""
        if explicit_line:
            if explicit_line in caption:
                return caption
            return caption + "\n\n" + explicit_line

        community = set(self.config.get("community_categories", []))
        if category in community:
            return caption

        caption_source_categories = set(self.config.get("caption_source_categories", []))
        if category in caption_source_categories and sources:
            publishers = []
            for record in sources:
                publisher = record["publisher"]
                if publisher and publisher not in publishers:
                    publishers.append(publisher)
            if publishers and not any(publisher in caption for publisher in publishers):
                return caption + "\n\n참고: " + ", ".join(publishers)
        return caption

    def _sources_text(self, sources: List[Dict[str, str]], category: Optional[str]) -> str:
        lines = ["# 내부 제작 기록용 출처 (공개 본문 아님)", ""]
        if not sources:
            lines.append("supplied sources: none")
            community = set(self.config.get("community_categories", []))
            if category in community:
                lines.append(
                    "community story: 공개 본문 출처 표기는 강제하지 않으며, 원문이 있으면 여기에만 보관한다"
                )
        for position, record in enumerate(sources, start=1):
            label = record["publisher"] or "(publisher unknown)"
            line = f"{position}. {label}"
            if record["title"]:
                line += f" — {record['title']}"
            if record["url"]:
                line += f" — {record['url']}"
            if record["note"]:
                line += f" ({record['note']})"
            lines.append(line)
        return "\n".join(lines) + "\n"

    def _preview_html(
        self,
        title: str,
        category: Optional[str],
        slide_records: List[Dict[str, Any]],
        caption: str,
    ) -> str:
        safe_title = html.escape(title or "CardNews publish package")
        safe_category = html.escape(category or "")
        parts = [
            "<!DOCTYPE html>",
            "<html lang=\"ko\">",
            "<head>",
            "<meta charset=\"utf-8\">",
            f"<title>{safe_title}</title>",
            "<style>body{font-family:sans-serif;max-width:720px;margin:24px auto;"
            "padding:0 16px}img,video{width:100%;display:block;margin:12px 0}"
            "pre{white-space:pre-wrap;background:#f5f5f5;padding:12px}</style>",
            "</head>",
            "<body>",
            f"<h1>{safe_title}</h1>",
            f"<p>{safe_category} · manual upload preview</p>",
        ]
        for record in slide_records:
            file_name = html.escape(Path(str(record["file"])).name)
            extension = Path(str(record["file"])).suffix.lower()
            if extension in VIDEO_EXTENSIONS:
                parts.append(f"<video src=\"{file_name}\" controls></video>")
            else:
                parts.append(f"<img src=\"{file_name}\" alt=\"{file_name}\">")
        parts.extend([
            "<h2>Caption</h2>",
            f"<pre>{html.escape(caption)}</pre>",
            "</body>",
            "</html>",
        ])
        return "\n".join(parts) + "\n"

    def _write_manifest(self, package_dir: Path, manifest: Dict[str, Any]) -> None:
        try:
            package_dir.mkdir(parents=True, exist_ok=True)
            (package_dir / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            manifest["warnings"].append(
                f"manifest.json could not be written ({type(exc).__name__})"
            )
