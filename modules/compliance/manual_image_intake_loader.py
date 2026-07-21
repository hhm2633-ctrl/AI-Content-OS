"""Fail-closed loader for operator-supplied Manual Image Intake (V2.0).

An operator can supply 1 to 20 real images to replace the CardNews module's
generated/fallback images for specific card slots, each bound to a validated
rights record.  This module never decides whether a card is publishable and
never touches an already-committed/immutable output set; it only validates
raw operator input so `WorkflowEngine` can safely substitute real image
bytes into the still-mutable, run-scoped scratch directory *before*
`CardNewsOutputSetTransaction.stage()` commits anything.

Real intake file location: ``storage/manual_image_intake/<output_set_id>.json``.

Expected file schema::

    {
      "output_set_id": "<must equal the active committed output_set_id>",
      "images": [
        {
          "card_index": 1,            // 1..20, unique within the file
          "image_path": "<repo-relative path to a real image file>",
          "rights_record": {
            "origin": "first_party|user_supplied|approved_external",
            "role": "topic_evidence|decorative",
            "rights_status": "<value valid for origin>",
            "rights_review_status": "approved",
            "rights_reviewed_at": "<ISO-8601 aware timestamp>",
            "reference_url": "<public URL or repo-relative bound local record>",
            "reference_verified": true,
            "source_name": "<non-placeholder text>",
            "evidence_captured_at": "<ISO-8601 aware timestamp>",
            "evidence_reviewed_at": "<ISO-8601 aware timestamp>",
            "topic_relevance": "<non-placeholder text>",
            "authenticity_status": "verified",
            "attribution_required": bool,
            "attribution_text": "<required, non-placeholder, only if attribution_required>",
            "operator_checklist": {
              "source_opened": true, "rights_reviewed": true, "claims_reviewed": true,
              "attribution_reviewed": true, "final_asset_reviewed": true
            }
          }
        },
        ... 1 to 20 entries ...
      ]
    }

Unlike `rights_intake_loader.load_verified_rights_intake` (which rejects an
entire file on any single defect, because it represents one coherent
publish-readiness decision), this loader validates **each image entry
independently**: "1 to 20 images" is an explicit statement that partial
coverage is expected, so a malformed entry is simply excluded rather than
invalidating the whole file. An absolute path, a `.runs`/`.staging` path, a
corrupt/wrong-size image, or a missing/invalid rights record causes that one
entry to be rejected -- never applied, never partially applied.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image

from modules.card_news.canvas_contract import (
    MAX_ALLOWED_CARD_SLIDE_COUNT,
    is_allowed_card_canvas_size,
)
from modules.compliance.rights_intake_loader import _text, validate_card_rights_record

_INTAKE_DIR = Path("storage/manual_image_intake")
_STAGED_INTAKE_DIR = _INTAKE_DIR / "staged"
_MAX_IMAGES = MAX_ALLOWED_CARD_SLIDE_COUNT


def _repo_root() -> Path:
    return Path(".").resolve()


def _rejects_scratch_path(path_text: str) -> bool:
    if not path_text or Path(path_text).is_absolute():
        return True
    lowered = path_text.replace("\\", "/").lower().split("/")
    return ".runs" in lowered or ".staging" in lowered


def _existing_repo_relative_file(path_text: str):
    if not path_text or _rejects_scratch_path(path_text):
        return None
    root = _repo_root()
    try:
        resolved = (root / path_text).resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError):
        return None
    return resolved if resolved.is_file() else None


def _decodable_expected_size_image(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
            size = image.size
            fmt = image.format
    except (OSError, ValueError):
        return False
    return is_allowed_card_canvas_size(size) and fmt == "PNG"


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 64), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_verified_manual_images(output_set_id: str) -> Dict[int, Dict[str, Any]]:
    """Return validated manual image entries keyed by card_index (1-20).

    An empty dict means: no genuine manual image applies to any slot for
    this exact output set, and the caller must keep every CardNews-generated
    fallback image untouched.  Never raises.
    """
    try:
        return _load_verified_manual_images(output_set_id)
    except Exception:
        return {}


def _load_verified_manual_images(output_set_id: str) -> Dict[int, Dict[str, Any]]:
    trusted_output_set_id = _text(output_set_id)
    if not trusted_output_set_id:
        return {}

    path = _INTAKE_DIR / f"{trusted_output_set_id}.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    if _text(data.get("output_set_id")) != trusted_output_set_id:
        return {}

    return _validate_image_entries(data.get("images"))


def load_staged_manual_images(content_id: str) -> Dict[int, Dict[str, Any]]:
    """Return validated staged manual image entries keyed by card_index (1-20).

    Staged intake (``storage/manual_image_intake/staged/<content_id>.json``)
    exists precisely because a fresh workflow run's ``output_set_id`` is a
    random value generated only once the run starts, so an operator cannot
    pre-write an intake file keyed by an ID that does not exist yet. Staged
    entries are keyed by a stable operator-chosen ``content_id`` instead, and
    are bound to a real committed ``output_set_id`` only later, by
    `WorkflowEngine.apply_staged_manual_image_intake_to_active_set`, which
    computes each image's SHA-256 fresh at that binding step against the
    exact committed card path it is about to replace. Never raises.
    """
    try:
        return _load_staged_manual_images(content_id)
    except Exception:
        return {}


def _load_staged_manual_images(content_id: str) -> Dict[int, Dict[str, Any]]:
    trusted_content_id = _text(content_id)
    if not trusted_content_id:
        return {}

    path = _STAGED_INTAKE_DIR / f"{trusted_content_id}.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    if _text(data.get("content_id")) != trusted_content_id:
        return {}

    return _validate_image_entries(data.get("images"))


def _validate_image_entries(images: Any) -> Dict[int, Dict[str, Any]]:
    if not isinstance(images, list) or not (1 <= len(images) <= _MAX_IMAGES):
        return {}

    accepted: Dict[int, Dict[str, Any]] = {}
    duplicate_indices = set()
    seen_indices = set()

    for entry in images:
        if not isinstance(entry, dict):
            continue
        try:
            index = int(entry.get("card_index"))
        except (TypeError, ValueError):
            continue
        if isinstance(index, bool) or not (1 <= index <= _MAX_IMAGES):
            continue
        if index in seen_indices:
            duplicate_indices.add(index)
            continue
        seen_indices.add(index)

        image_path = entry.get("image_path")
        image_path_text = image_path if isinstance(image_path, str) else ""
        resolved = _existing_repo_relative_file(image_path_text)
        if resolved is None or not _decodable_expected_size_image(resolved):
            continue

        asset_id = f"manual_image_{index}"
        rights_record = validate_card_rights_record(entry.get("rights_record"), asset_id)
        if rights_record is None:
            continue

        accepted[index] = {
            "image_path": Path(image_path_text).as_posix(),
            "resolved_path": resolved,
            "sha256": _sha256_of(resolved),
            "rights_record": rights_record,
        }

    for index in duplicate_indices:
        # An index claimed by more than one entry is ambiguous; never guess
        # which one the operator meant, so neither is applied.
        accepted.pop(index, None)

    return accepted
