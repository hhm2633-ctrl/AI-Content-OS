"""Localize approved source-editorial media candidates for CardNews rendering."""

from __future__ import annotations

import copy
import hashlib
import ipaddress
import re
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Mapping
from urllib.parse import urlparse

from PIL import Image

from modules.media_intelligence.source_media_quality_gate import (
    SourceMediaQualityGate,
)


MAX_DOWNLOAD_BYTES = 15 * 1024 * 1024
_SAFE_ID = re.compile(r"[^0-9A-Za-z._-]+")
_TOKEN = re.compile(r"[0-9A-Za-z가-힣]{2,}")
_STOP_TOKENS = {
    "관련",
    "변화",
    "사실",
    "이후",
    "대한",
    "통해",
    "한다",
    "있다",
    "가구",
}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _safe_remote_url(value: Any) -> str:
    url = _text(value)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    host = parsed.hostname.casefold()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        return ""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return url
    return "" if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
    ) else url


def _candidate_allowed(candidate: Mapping[str, Any]) -> bool:
    return (
        _text(candidate.get("rights_status")) in {
            "source_editorial_usable",
            "public_domain",
            "open_license",
        }
        and candidate.get("topic_relevant") is True
        and candidate.get("attribution_required") is True
        and candidate.get("publish_authorized") is False
        and bool(_text(candidate.get("source_url")))
        and bool(_safe_remote_url(candidate.get("remote_url")))
    )


def _tokens(value: Any) -> set[str]:
    return {
        token.casefold()
        for token in _TOKEN.findall(_text(value))
        if token.casefold() not in _STOP_TOKENS
    }


def _slide_tokens(slide: Mapping[str, Any]) -> set[str]:
    visual = slide.get("visual_spec")
    visual = visual if isinstance(visual, Mapping) else {}
    return _tokens(
        " ".join(
            _text(value)
            for value in (
                slide.get("headline"),
                slide.get("body"),
                visual.get("source_fact"),
                visual.get("question"),
            )
        )
    )


def _candidate_score(
    candidate: Mapping[str, Any],
    slide: Mapping[str, Any],
    ignored_tokens: set[str],
) -> int:
    slide_tokens = _slide_tokens(slide) - ignored_tokens
    candidate_tokens = _tokens(
        " ".join(
            _text(value)
            for value in (
                candidate.get("title"),
                candidate.get("description"),
                candidate.get("channel"),
                candidate.get("publisher"),
            )
        )
    )
    return len(slide_tokens & candidate_tokens)


def _assign_candidates(
    candidates: list[Dict[str, Any]],
    slides: list[Any],
) -> list[Dict[str, Any]]:
    if not candidates:
        return []
    source_images = [
        candidate
        for candidate in candidates
        if _text(candidate.get("media_type")) in {"news_image", "open_image"}
    ] or candidates
    token_frequency = Counter(
        token
        for raw_slide in slides
        for token in _slide_tokens(
            raw_slide if isinstance(raw_slide, Mapping) else {}
        )
    )
    common_threshold = max(2, (len(slides) + 1) // 2)
    ignored_tokens = {
        token
        for token, frequency in token_frequency.items()
        if frequency >= common_threshold
    }
    usage = {id(candidate): 0 for candidate in candidates}
    assigned: list[Dict[str, Any]] = []
    for index, raw_slide in enumerate(slides):
        slide = raw_slide if isinstance(raw_slide, Mapping) else {}
        scored = [
            (
                _candidate_score(candidate, slide, ignored_tokens),
                -usage[id(candidate)],
                -position,
                candidate,
            )
            for position, candidate in enumerate(candidates)
        ]
        best = max(scored, key=lambda row: row[:3])
        if best[0] > 0:
            selected = best[3]
        else:
            selected = source_images[index % len(source_images)]
        usage[id(selected)] += 1
        assigned.append(selected)
    return assigned


def _download_image(url: str, destination: Path) -> tuple[int, int]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; AI-Content-OS editorial intake)",
            "Accept": "image/avif,image/webp,image/png,image/jpeg,*/*;q=0.4",
        },
    )
    temporary = destination.with_suffix(".download")
    total = 0
    with urllib.request.urlopen(request, timeout=20) as response, temporary.open("wb") as output:
        content_type = _text(response.headers.get("Content-Type")).casefold()
        if content_type and not content_type.startswith("image/"):
            raise ValueError("remote response is not an image")
        while True:
            chunk = response.read(64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_DOWNLOAD_BYTES:
                raise ValueError("remote image exceeds download limit")
            output.write(chunk)
    if total <= 0:
        raise ValueError("remote image is empty")
    with Image.open(temporary) as image:
        image.load()
        width, height = image.size
        normalized = image.convert("RGBA") if image.mode in {"RGBA", "LA"} else image.convert("RGB")
        normalized.save(destination, format="PNG", optimize=True)
    temporary.unlink(missing_ok=True)
    return width, height


def localize_source_editorial_media(
    package: Any,
    output_root: str | Path,
    *,
    quality_gate: Any | None = None,
) -> Dict[str, Any]:
    if not isinstance(package, Mapping):
        return {"status": "blocked", "reason_code": "package_required"}
    root = Path(output_root).expanduser().resolve()
    if root.drive.casefold() != "f:":
        return {"status": "blocked", "reason_code": "output_root_must_use_f_drive"}
    localized = copy.deepcopy(dict(package))
    evidence = localized.get("evidence")
    evidence = evidence if isinstance(evidence, dict) else {}
    assets = evidence.get("assets")
    assets = assets if isinstance(assets, list) else []
    root.mkdir(parents=True, exist_ok=True)
    localized_by_id: Dict[str, Dict[str, Any]] = {}
    localized_by_hash: Dict[str, Dict[str, Any]] = {}
    failures = []
    duplicate_count = 0
    for position, raw in enumerate(assets, start=1):
        if not isinstance(raw, dict) or not _candidate_allowed(raw):
            continue
        asset_id = _text(raw.get("asset_id")) or f"source-editorial-{position}"
        remote_url = _safe_remote_url(raw.get("remote_url"))
        safe_id = _SAFE_ID.sub("-", asset_id).strip("-") or hashlib.sha256(
            remote_url.encode("utf-8")
        ).hexdigest()[:16]
        destination = root / f"{safe_id}.png"
        try:
            width, height = _download_image(remote_url, destination)
        except Exception as exc:
            failures.append({"asset_id": asset_id, "reason": type(exc).__name__})
            continue
        raw.update(
            {
                "local_path": str(destination),
                "localized": True,
                "width": width,
                "height": height,
                "manual_visual_review_required": True,
                "publish_authorized": False,
            }
        )
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        if digest in localized_by_hash:
            duplicate_count += 1
            duplicate = copy.deepcopy(localized_by_hash[digest])
            duplicate["asset_id"] = asset_id
            localized_by_id[asset_id] = duplicate
            continue
        raw["content_sha256"] = digest
        localized_by_hash[digest] = copy.deepcopy(raw)
        localized_by_id[asset_id] = copy.deepcopy(raw)

    unique_candidates = list(localized_by_hash.values())
    if unique_candidates:
        evidence["assets"] = copy.deepcopy(unique_candidates)
    slides = localized.get("slides")
    slides = slides if isinstance(slides, list) else []

    # Remove compiler-time suggestions before evaluating the actual localized
    # pixels.  A source URL or metadata match must never reach the renderer as
    # if OCR/OpenCLIP had approved the image itself.
    for slide in slides:
        if not isinstance(slide, dict):
            continue
        visual_spec = slide.get("visual_spec")
        if not isinstance(visual_spec, dict):
            continue
        visual_spec.pop("source_media_candidate", None)
    media_plan = localized.get("media_plan")
    media_plan = media_plan if isinstance(media_plan, list) else []
    for row in media_plan:
        if not isinstance(row, dict):
            continue
        row.pop("source_media_candidate", None)

    gate = quality_gate if quality_gate is not None else SourceMediaQualityGate()
    gate_receipts: list[Dict[str, Any]] = []
    selected_assets: list[Dict[str, Any]] = []
    used_asset_keys: set[str] = set()
    required_slide_count = 0
    blocked_slide_count = 0

    for slide_index, slide in enumerate(slides):
        if not isinstance(slide, dict):
            continue
        visual_spec = slide.get("visual_spec")
        visual_spec = visual_spec if isinstance(visual_spec, dict) else {}
        if _text(visual_spec.get("visual_type")) == "cta_prompt":
            gate_receipts.append(
                {
                    "page": slide.get("page"),
                    "status": "not_required",
                    "reason_code": "cta_slide_does_not_require_source_media",
                }
            )
            continue

        required_slide_count += 1
        labels_status = _text(
            visual_spec.get("visual_relevance_labels_status")
        )
        labels = visual_spec.get("visual_relevance_labels")
        if labels_status != "supplied" or not labels:
            receipt: Dict[str, Any] = {
                "status": "blocked",
                "reason_code": "visual_relevance_labels_missing",
                "passed_candidates": [],
                "rejected_candidates": [],
                "render_allowed": False,
            }
        elif not unique_candidates:
            receipt = {
                "status": "blocked",
                "reason_code": "localized_source_media_unavailable",
                "passed_candidates": [],
                "rejected_candidates": [],
                "render_allowed": False,
            }
        else:
            try:
                receipt = dict(
                    gate.evaluate(
                        unique_candidates,
                        headline=_text(slide.get("headline")),
                        body=_text(slide.get("body")),
                        bilingual_visual_labels=labels,
                    )
                )
            except Exception as exc:
                receipt = {
                    "status": "blocked",
                    "reason_code": (
                        f"source_media_quality_gate_failed:{type(exc).__name__}"
                    ),
                    "passed_candidates": [],
                    "rejected_candidates": [],
                    "render_allowed": False,
                }

        passed = receipt.get("passed_candidates")
        passed = passed if isinstance(passed, list) else []
        available = []
        for candidate in passed:
            if not isinstance(candidate, Mapping):
                continue
            key = _text(
                candidate.get("content_sha256")
                or candidate.get("asset_id")
                or candidate.get("local_path")
            )
            if key and key not in used_asset_keys:
                available.append(dict(candidate))
        available.sort(
            key=lambda item: float(
                (
                    item.get("quality_gate")
                    if isinstance(item.get("quality_gate"), Mapping)
                    else {}
                ).get("relevant_score")
                or -1.0
            ),
            reverse=True,
        )
        if receipt.get("render_allowed") is True and available:
            selected = available[0]
            selected_key = _text(
                selected.get("content_sha256")
                or selected.get("asset_id")
                or selected.get("local_path")
            )
            used_asset_keys.add(selected_key)
            selected_assets.append(copy.deepcopy(selected))
            visual_spec["source_media_candidate"] = copy.deepcopy(selected)
            if slide_index < len(media_plan) and isinstance(
                media_plan[slide_index], dict
            ):
                media_plan[slide_index]["source_media_candidate"] = copy.deepcopy(
                    selected
                )
            receipt["selected_asset_id"] = _text(selected.get("asset_id"))
            receipt["status"] = "passed"
        else:
            blocked_slide_count += 1
            receipt["status"] = "blocked"
            if receipt.get("render_allowed") is True and not available:
                receipt["reason_code"] = "unique_relevant_media_exhausted"
            receipt["render_allowed"] = False
        receipt["page"] = slide.get("page")
        gate_receipts.append(copy.deepcopy(receipt))

    quality_passed = (
        required_slide_count > 0
        and blocked_slide_count == 0
        and len(selected_assets) == required_slide_count
    )
    evidence["assets"] = copy.deepcopy(selected_assets)
    evidence["source_media_quality"] = {
        "status": "passed" if quality_passed else "blocked",
        "required_slide_count": required_slide_count,
        "passed_slide_count": len(selected_assets),
        "blocked_slide_count": blocked_slide_count,
        "unique_media_required": True,
        "tool_scores_are_internal_quality_proxies_only": True,
        "receipts": gate_receipts,
    }
    localized["evidence"] = evidence
    localized["media_plan"] = media_plan

    localized["source_editorial_localization"] = {
        "status": "completed" if quality_passed else "blocked",
        "localized_count": len(unique_candidates),
        "duplicate_count": duplicate_count,
        "failure_count": len(failures),
        "failures": failures,
        "output_root": str(root),
        "publish_authorized": False,
        "quality_gate_status": "passed" if quality_passed else "blocked",
        "required_slide_count": required_slide_count,
        "verified_unique_assignment_count": len(selected_assets),
    }
    if not quality_passed:
        localized["status"] = "blocked"
        localized["reason_code"] = "source_media_quality_gate_blocked"
        gates = localized.get("gates")
        gates = gates if isinstance(gates, dict) else {}
        gates["render"] = {
            "status": "blocked",
            "authorized": False,
            "reason_code": "source_media_quality_gate_blocked",
        }
        localized["gates"] = gates
    return localized


__all__ = ["localize_source_editorial_media"]
