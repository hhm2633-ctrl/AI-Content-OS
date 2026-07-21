"""Category-first media pack builder for owner-selected CardNews topics.

Manual production path. It validates already-discovered media candidates for a
single reviewed topic, copies local files into the package ``media_pack``
directory, and keeps remote URLs as manifest references unless an explicit
opt-in download mode fetches only the supplied URLs under timeout/size/type
limits. It never searches for new media, never publishes, and never raises out
of ``build`` — failures degrade to an honest blocked/diagnostic manifest.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

DEFAULT_CONFIG_PATH = Path("config/cardnews_category_packages.json")

FALLBACK_CONFIG: Dict[str, Any] = {
    "category_bucket_map": {
        "major_news_policy": "news_policy_society",
        "incident_conflict": "news_incident",
        "economy_market": "news_economy_market",
        "entertainment_relationship": "relationship_entertainment",
        "community_buzz": "community_story",
    },
    "split_category": "beauty_fashion",
    "beauty_fashion_split": {
        "metadata_fields": ["vertical", "canonical_category", "category_detail", "editorial_scope"],
        "allowed_values": {"fashion": "fashion", "beauty": "beauty", "패션": "fashion", "뷰티": "beauty"},
    },
    "canonical_categories": [
        "news_policy_society",
        "news_incident",
        "news_economy_market",
        "relationship_entertainment",
        "community_story",
        "fashion",
        "beauty",
    ],
    "allowed_media_types": ["image", "video", "screenshot", "editorial", "motion_graphic"],
    "allowed_origins": ["official", "news", "community", "generated", "local_created"],
    "allowed_asset_classes": ["source_evidence", "auxiliary"],
    "allowed_local_extensions": [".png", ".jpg", ".jpeg", ".webp", ".mp4"],
    "reference_only_agencies": ["ap", "ap통신", "associated press", "the associated press"],
    "download": {
        "enabled_by_default": False,
        "timeout_seconds": 10,
        "max_bytes": 26214400,
        "allowed_schemes": ["https", "http"],
        "allowed_content_types": {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/webp": ".webp",
            "video/mp4": ".mp4",
        },
    },
}

# fetcher(url, timeout_seconds, max_bytes) -> (payload, content_type)
Fetcher = Callable[[str, float, int], Tuple[bytes, str]]


def load_package_config(config_path: Optional[Path] = None) -> Tuple[Dict[str, Any], List[str]]:
    """Load the package config with an explicit fallback record."""
    warnings: List[str] = []
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("config root must be an object")
        return data, warnings
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        warnings.append(
            f"package config unavailable ({type(exc).__name__}); fallback configuration used"
        )
        return dict(FALLBACK_CONFIG), warnings


def resolve_category(topic_input: Any, config: Dict[str, Any]) -> Dict[str, Any]:
    """Map the supplied category to one canonical bucket, or block honestly."""
    raw = topic_input.get("category") if isinstance(topic_input, dict) else None
    result: Dict[str, Any] = {
        "status": "blocked",
        "input_category": raw if isinstance(raw, str) else None,
        "canonical_category": None,
        "reason": "",
    }
    if not isinstance(raw, str) or not raw.strip():
        result["reason"] = "category_missing: reviewed input has no category field"
        return result

    raw_value = raw.strip()
    bucket_map = config.get("category_bucket_map", {})
    canonical = set(config.get("canonical_categories", []))
    split_category = config.get("split_category", "beauty_fashion")

    if raw_value in canonical:
        result.update({"status": "resolved", "canonical_category": raw_value})
        return result
    if raw_value in bucket_map:
        result.update({"status": "resolved", "canonical_category": bucket_map[raw_value]})
        return result
    if raw_value == split_category:
        split = config.get("beauty_fashion_split", {})
        allowed_values = split.get("allowed_values", {})
        for field in split.get("metadata_fields", []):
            value = topic_input.get(field)
            if isinstance(value, str) and value.strip().lower() in allowed_values:
                result.update({
                    "status": "resolved",
                    "canonical_category": allowed_values[value.strip().lower()],
                    "reason": f"split from {split_category} via {field}",
                })
                return result
        result["reason"] = (
            "beauty_fashion_vertical_missing: beauty_fashion requires explicit "
            "fashion/beauty metadata; blocking instead of guessing"
        )
        return result

    result["reason"] = f"category_unknown: '{raw_value}' has no canonical bucket"
    return result


def build_topic_slug(topic_input: Any) -> str:
    """Deterministic filesystem-safe slug from supplied topic identity."""
    candidates = []
    if isinstance(topic_input, dict):
        candidates = [topic_input.get("topic_slug"), topic_input.get("topic_id"), topic_input.get("title")]
    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        slug = re.sub(r"[^a-z0-9_-]+", "-", candidate.strip().lower()).strip("-")
        slug = re.sub(r"-{2,}", "-", slug)
        if len(slug) >= 3:
            return slug[:80]
        digest = hashlib.sha1(candidate.strip().encode("utf-8")).hexdigest()[:10]
        return f"topic-{digest}"
    return "topic-unknown"


def _default_fetcher(url: str, timeout_seconds: float, max_bytes: int) -> Tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "AI-Content-OS-package/1.0"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        content_type = str(response.headers.get("Content-Type", "")).split(";")[0].strip().lower()
        payload = response.read(max_bytes + 1)
    return payload, content_type


class CategoryMediaPackBuilder:
    """Validate and inventory supplied media candidates for one reviewed topic."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        config_path: Optional[Path] = None,
        fetcher: Optional[Fetcher] = None,
    ):
        self.config_warnings: List[str] = []
        if config is not None:
            self.config = config
        else:
            self.config, self.config_warnings = load_package_config(config_path)
        self.fetcher: Fetcher = fetcher or _default_fetcher

    def build(
        self,
        topic_input: Any,
        package_dir: Path,
        download_remote: bool = False,
        local_media_root: Optional[Path] = None,
    ) -> Dict[str, Any]:
        try:
            return self._build(topic_input, Path(package_dir), download_remote, local_media_root)
        except Exception as exc:  # never escape the builder
            return self._blocked_result(
                topic_input,
                reason=f"internal_error: media pack builder failed ({type(exc).__name__})",
                download_remote=download_remote,
            )

    def _build(
        self,
        topic_input: Any,
        package_dir: Path,
        download_remote: bool,
        local_media_root: Optional[Path],
    ) -> Dict[str, Any]:
        if not isinstance(topic_input, dict):
            return self._blocked_result(
                topic_input,
                reason="input_invalid: reviewed topic input must be a JSON object",
                download_remote=download_remote,
            )

        warnings = list(self.config_warnings)
        blocking_reasons: List[str] = []
        category = resolve_category(topic_input, self.config)
        if category["status"] != "resolved":
            blocking_reasons.append(category["reason"])

        raw_items = topic_input.get("slides")
        if raw_items is None:
            raw_items = topic_input.get("media", [])
        if not isinstance(raw_items, list) or not raw_items:
            blocking_reasons.append("media_missing: no slide/media candidates were supplied")
            raw_items = []

        media_pack_dir = Path(package_dir) / "media_pack"
        items: List[Dict[str, Any]] = []
        normalized = self._normalize_items(raw_items, warnings)
        for sequence, record in enumerate(normalized, start=1):
            items.append(
                self._process_item(
                    record,
                    sequence,
                    media_pack_dir,
                    download_remote,
                    local_media_root,
                )
            )

        counts = {
            "total": len(items),
            "packaged": sum(1 for item in items if item["status"] == "packaged"),
            "downloaded": sum(1 for item in items if item["status"] == "downloaded"),
            "remote_reference": sum(1 for item in items if item["status"] == "remote_reference"),
            "reference_only": sum(1 for item in items if item["reference_only"]),
            "blocked": sum(1 for item in items if item["status"] == "blocked"),
            "invalid": sum(1 for item in items if item["status"] in ("invalid", "download_failed")),
        }
        publishable = sum(1 for item in items if item["publishable"])
        if items and publishable == 0:
            blocking_reasons.append(
                "no_publishable_media: no supplied candidate became a local publishable asset"
            )

        status = "media_pack_ready" if not blocking_reasons else "media_pack_blocked"
        result = {
            "schema_version": "category_media_pack_v1",
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "topic_id": str(topic_input.get("topic_id", "")),
            "topic_slug": build_topic_slug(topic_input),
            "title": str(topic_input.get("title", "")),
            "category": category,
            "download_mode": bool(download_remote),
            "items": items,
            "counts": counts,
            "publishable_items": publishable,
            "blocking_reasons": blocking_reasons,
            "warnings": warnings,
            "fallback_used": bool(blocking_reasons or self.config_warnings),
            "validation_scope": "file-level existence/size/type checks; media content is not decoded",
        }
        self._write_pack_json(media_pack_dir, result, warnings)
        return result

    def _blocked_result(
        self, topic_input: Any, reason: str, download_remote: bool
    ) -> Dict[str, Any]:
        return {
            "schema_version": "category_media_pack_v1",
            "status": "media_pack_blocked",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "topic_id": str(topic_input.get("topic_id", "")) if isinstance(topic_input, dict) else "",
            "topic_slug": build_topic_slug(topic_input),
            "title": str(topic_input.get("title", "")) if isinstance(topic_input, dict) else "",
            "category": resolve_category(topic_input, self.config),
            "download_mode": bool(download_remote),
            "items": [],
            "counts": {
                "total": 0,
                "packaged": 0,
                "downloaded": 0,
                "remote_reference": 0,
                "reference_only": 0,
                "blocked": 0,
                "invalid": 0,
            },
            "publishable_items": 0,
            "blocking_reasons": [reason],
            "warnings": list(self.config_warnings),
            "fallback_used": True,
            "validation_scope": "file-level existence/size/type checks; media content is not decoded",
        }

    def _normalize_items(
        self, raw_items: List[Any], warnings: List[str]
    ) -> List[Dict[str, Any]]:
        allowed_media_types = set(self.config.get("allowed_media_types", []))
        allowed_origins = set(self.config.get("allowed_origins", []))
        allowed_asset_classes = set(self.config.get("allowed_asset_classes", []))

        normalized: List[Dict[str, Any]] = []
        for position, raw in enumerate(raw_items, start=1):
            if not isinstance(raw, dict):
                warnings.append(f"media item {position} is not an object and was skipped")
                continue
            order = raw.get("order")
            if not isinstance(order, int) or isinstance(order, bool) or order < 1:
                order = position
            media_type = str(raw.get("media_type", "image")).strip().lower() or "image"
            if allowed_media_types and media_type not in allowed_media_types:
                warnings.append(f"media item {position} has unknown media_type '{media_type}'")
            origin = str(raw.get("origin", "")).strip().lower()
            if not origin:
                origin = "unknown"
                warnings.append(f"media item {position} has no origin; recorded as 'unknown'")
            elif allowed_origins and origin not in allowed_origins:
                warnings.append(f"media item {position} has unknown origin '{origin}'")
            asset_class = str(raw.get("asset_class", raw.get("usage", "auxiliary"))).strip().lower()
            if asset_class not in allowed_asset_classes:
                warnings.append(
                    f"media item {position} has unknown asset_class '{asset_class}'; treated as auxiliary"
                )
                asset_class = "auxiliary"
            normalized.append({
                "input_position": position,
                "order": order,
                "slide_role": str(raw.get("slide_role", "slide")).strip() or "slide",
                "media_type": media_type,
                "origin": origin,
                "asset_class": asset_class,
                "source_url": str(raw.get("source_url", "")).strip(),
                "publisher": str(raw.get("publisher", "")).strip(),
                "brand": str(raw.get("brand", "")).strip(),
                "agency": str(raw.get("agency", "")).strip(),
                "ap_source": raw.get("ap_source") is True,
                "local_path": str(raw.get("local_path", "")).strip(),
                "remote_url": str(raw.get("remote_url", "")).strip(),
            })
        normalized.sort(key=lambda item: (item["order"], item["input_position"]))
        return normalized

    def _process_item(
        self,
        record: Dict[str, Any],
        sequence: int,
        media_pack_dir: Path,
        download_remote: bool,
        local_media_root: Optional[Path],
    ) -> Dict[str, Any]:
        item = {
            "sequence": sequence,
            "order": record["order"],
            "slide_role": record["slide_role"],
            "media_type": record["media_type"],
            "origin": record["origin"],
            "asset_class": record["asset_class"],
            "source_url": record["source_url"],
            "publisher": record["publisher"],
            "brand": record["brand"],
            "local_path": record["local_path"] or None,
            "remote_url": record["remote_url"] or None,
            "packaged_file": None,
            "status": "invalid",
            "publishable": False,
            "reference_only": False,
            "diagnostics": [],
        }

        if self._is_reference_only_agency(record):
            item["reference_only"] = True
            item["status"] = "reference_only"
            item["diagnostics"].append(
                "AP/Associated Press material stays a discovery reference and is never "
                "promoted into a publishable asset"
            )
            return item

        if record["asset_class"] == "source_evidence" and (
            record["origin"] == "generated" or record["media_type"] == "motion_graphic"
        ):
            item["status"] = "blocked"
            item["diagnostics"].append(
                "generated/animated media must not be presented as source footage or evidence"
            )
            return item

        if record["local_path"]:
            return self._package_local(item, record, sequence, media_pack_dir, local_media_root)
        if record["remote_url"]:
            if not download_remote:
                item["status"] = "remote_reference"
                item["diagnostics"].append(
                    "remote URL kept as manifest reference; download mode was not enabled"
                )
                return item
            return self._download_remote(item, record, sequence, media_pack_dir)

        item["diagnostics"].append("media candidate has neither local_path nor remote_url")
        return item

    def _is_reference_only_agency(self, record: Dict[str, Any]) -> bool:
        if record.get("ap_source"):
            return True
        agencies = {
            str(value).strip().lower()
            for value in self.config.get("reference_only_agencies", [])
        }
        for field in ("publisher", "brand", "agency"):
            value = record.get(field, "").strip().lower()
            if not value:
                continue
            if value in agencies or "associated press" in value:
                return True
        return False

    def _package_local(
        self,
        item: Dict[str, Any],
        record: Dict[str, Any],
        sequence: int,
        media_pack_dir: Path,
        local_media_root: Optional[Path],
    ) -> Dict[str, Any]:
        source = Path(record["local_path"])
        if not source.is_absolute():
            source = Path(local_media_root or Path.cwd()) / source
        if not source.is_file():
            item["diagnostics"].append(f"local file is missing: {record['local_path']}")
            return item
        try:
            if source.stat().st_size <= 0:
                item["diagnostics"].append(f"local file is empty: {record['local_path']}")
                return item
        except OSError as exc:
            item["diagnostics"].append(
                f"local file is unreadable: {record['local_path']} ({type(exc).__name__})"
            )
            return item

        extension = source.suffix.lower()
        allowed = set(self.config.get("allowed_local_extensions", []))
        if allowed and extension not in allowed:
            item["diagnostics"].append(
                f"local file type '{extension}' is not an allowed package media type"
            )
            return item

        target = media_pack_dir / self._packaged_name(sequence, record, extension)
        try:
            media_pack_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        except OSError as exc:
            item["diagnostics"].append(
                f"local file could not be copied into the package ({type(exc).__name__})"
            )
            return item

        item["packaged_file"] = f"media_pack/{target.name}"
        item["status"] = "packaged"
        item["publishable"] = True
        return item

    def _download_remote(
        self,
        item: Dict[str, Any],
        record: Dict[str, Any],
        sequence: int,
        media_pack_dir: Path,
    ) -> Dict[str, Any]:
        download = self.config.get("download", {})
        allowed_schemes = set(download.get("allowed_schemes", ["https", "http"]))
        allowed_types = download.get("allowed_content_types", {})
        timeout_seconds = float(download.get("timeout_seconds", 10))
        max_bytes = int(download.get("max_bytes", 26214400))
        url = record["remote_url"]

        scheme = url.split(":", 1)[0].lower() if ":" in url else ""
        if scheme not in allowed_schemes:
            item["status"] = "download_failed"
            item["diagnostics"].append(f"remote URL scheme '{scheme}' is not allowed for download")
            return item

        try:
            payload, content_type = self.fetcher(url, timeout_seconds, max_bytes)
        except Exception as exc:
            item["status"] = "download_failed"
            item["diagnostics"].append(
                f"download failed ({type(exc).__name__}); URL kept as manifest reference"
            )
            return item

        if len(payload) > max_bytes:
            item["status"] = "download_failed"
            item["diagnostics"].append(
                f"download exceeded the {max_bytes}-byte limit and was discarded"
            )
            return item
        if content_type not in allowed_types:
            item["status"] = "download_failed"
            item["diagnostics"].append(
                f"content type '{content_type}' is not an allowed download media type"
            )
            return item
        if not payload:
            item["status"] = "download_failed"
            item["diagnostics"].append("download returned an empty payload")
            return item

        target = media_pack_dir / self._packaged_name(sequence, record, allowed_types[content_type])
        try:
            media_pack_dir.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        except OSError as exc:
            item["status"] = "download_failed"
            item["diagnostics"].append(
                f"downloaded payload could not be written ({type(exc).__name__})"
            )
            return item

        item["packaged_file"] = f"media_pack/{target.name}"
        item["status"] = "downloaded"
        item["publishable"] = True
        return item

    def _packaged_name(self, sequence: int, record: Dict[str, Any], extension: str) -> str:
        role = re.sub(r"[^a-z0-9_-]+", "-", record["slide_role"].lower()).strip("-") or "slide"
        return f"item_{sequence:02d}_{role[:24]}{extension}"

    def _write_pack_json(
        self, media_pack_dir: Path, result: Dict[str, Any], warnings: List[str]
    ) -> None:
        try:
            media_pack_dir.mkdir(parents=True, exist_ok=True)
            (media_pack_dir / "media_pack.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            warnings.append(f"media_pack.json could not be written ({type(exc).__name__})")
