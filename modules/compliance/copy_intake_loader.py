"""Fail-closed loader for an operator-approved CardNews Copy Intake contract.

This module never decides whether a card is publishable and never renders or
edits anything. It only checks that an operator-supplied "approved copy"
record is structurally genuine (1..20 slides, contiguous indexes, non-placeholder
title/headline/body, a well-formed SHA-256 per slide, and role-based CTA
consistency) before `WorkflowEngine.create_release_revision` is allowed to use
it as the sole source of slide text/CTA for a brand-new, clean CardNews result.
It never itself compares the recorded image_sha256 against an actual committed
file -- that binding check belongs to the caller, which is the only place that
knows the real committed card paths.

Real intake file location: ``storage/copy_intake/<content_id>.json``.

Expected file schema::

    {
      "content_id": "CN-006",
      "title": "<non-placeholder title>",
      "operator_id": "<non-placeholder operator identity>",
      "approved_at": "<ISO-8601 aware timestamp, not in the future>",
      "slides": [
        {
          "slide_index": 1,
          "role": "cover",
          "headline": "<non-placeholder text>",
          "body": "<non-placeholder text>",
          "image_sha256": "<64 lowercase hex chars>",
          "cta_type": "",
          "cta_label": ""
        },
        { "slide_index": 2, "role": "...", ... },
        ...
        {
          "slide_index": "<last>",
          "role": "cta",
          "headline": "...", "body": "...", "image_sha256": "...",
          "cta_type": "<non-empty>",
          "cta_label": "<non-placeholder>"
        }
      ]
    }

Any structural defect, placeholder value, missing field, wrong type, wrong
slide count, wrong/duplicate slide_index, missing role, malformed SHA-256, a
CTA field on a non-CTA slide, or a missing CTA on CTA slides causes the whole
file to be rejected (``None`` is returned) -- there is no partial application.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from modules.card_news.canvas_contract import is_allowed_card_slide_count
from modules.compliance.rights_intake_loader import (
    _is_placeholder,
    _parse_aware_datetime,
    _text,
)

_INTAKE_DIR = Path("storage/copy_intake")
_CONTENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _valid_content_id(value: Any) -> str:
    text = _text(value)
    return text if text and _CONTENT_ID_PATTERN.match(text) else ""


def _valid_sha256(value: Any) -> str:
    text = _text(value).lower()
    return text if _SHA256_PATTERN.match(text) else ""


def load_verified_copy_intake(content_id: Any) -> Optional[Dict[str, Any]]:
    """Return a validated Copy Intake contract, or ``None`` if none applies.

    ``None`` means: no genuine, structurally complete, non-placeholder Copy
    Intake exists for this exact content_id, and the caller must never
    fabricate or partially apply slide copy in that case. Never raises.
    """
    try:
        return _load_verified_copy_intake(content_id)
    except Exception:
        return None


def _load_verified_copy_intake(content_id: Any) -> Optional[Dict[str, Any]]:
    trusted_content_id = _valid_content_id(content_id)
    if not trusted_content_id:
        return None

    path = _INTAKE_DIR / f"{trusted_content_id}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if _text(data.get("content_id")) != trusted_content_id:
        return None

    title = data.get("title")
    if _is_placeholder(title):
        return None

    operator_id = data.get("operator_id")
    if _is_placeholder(operator_id):
        return None

    approved_at = _parse_aware_datetime(data.get("approved_at"))
    if approved_at is None or approved_at > datetime.now(timezone.utc):
        return None

    slides_raw = data.get("slides")
    if not isinstance(slides_raw, list) or not is_allowed_card_slide_count(len(slides_raw)):
        return None

    by_index: Dict[int, Dict[str, Any]] = {}
    for slide in slides_raw:
        if not isinstance(slide, dict):
            return None
        try:
            index = int(slide.get("slide_index"))
        except (TypeError, ValueError):
            return None
        if index < 1 or index in by_index:
            return None
        by_index[index] = slide

    if sorted(by_index) != list(range(1, len(by_index) + 1)):
        return None

    ordered = [by_index[i] for i in range(1, len(by_index) + 1)]
    roles = [_text(slide.get("role")) for slide in ordered]
    if len(roles) != len(ordered) or any(_is_placeholder(role) for role in roles):
        return None

    normalized_slides: Dict[int, Dict[str, Any]] = {}
    for index, slide, role in zip(range(1, len(ordered) + 1), ordered, roles):
        headline = slide.get("headline")
        body = slide.get("body")
        if _is_placeholder(headline) or _is_placeholder(body):
            return None
        image_sha256 = _valid_sha256(slide.get("image_sha256"))
        if not image_sha256:
            return None
        cta_type = _text(slide.get("cta_type"))
        cta_label = _text(slide.get("cta_label"))
        if role == "cta":
            if not cta_type or _is_placeholder(cta_label):
                return None
        elif cta_type or cta_label:
            # Only slides explicitly marked as CTA may carry a call-to-action;
            # any other role carrying one is a structural defect, not a style
            # choice this loader may silently accept.
            return None
        normalized_slides[index] = {
            "slide_index": index,
            "role": role,
            "headline": _text(headline),
            "body": _text(body),
            "image_sha256": image_sha256,
            "cta_type": cta_type,
            "cta_label": cta_label,
        }

    return {
        "content_id": trusted_content_id,
        "title": _text(title),
        "operator_id": _text(operator_id),
        "approved_at": data.get("approved_at"),
        "slides": normalized_slides,
    }
