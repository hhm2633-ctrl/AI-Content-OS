"""Standalone local image intake for design learning.

The intake preserves source files, deduplicates only exact byte matches using
SHA-256, and produces an honest manifest, a unique staging directory, and a
Pillow contact sheet. It is deliberately not connected to WorkflowEngine.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageOps

from modules.design_learning.contact_sheet_generator import generate_contact_sheet


SCHEMA_VERSION = "local_image_intake_v1"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _is_below(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inspect_image(path: Path) -> Tuple[int, int, str]:
    with Image.open(path) as opened:
        transposed = ImageOps.exif_transpose(opened)
        transposed.load()
        return transposed.width, transposed.height, transposed.mode


def _write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary_path.replace(path)


def _base_entry(path: Path, source_root: Path) -> Dict[str, Any]:
    return {
        "asset_id": None,
        "source_relative_path": path.relative_to(source_root).as_posix(),
        "extension": path.suffix.lower(),
        "size_bytes": None,
        "width": None,
        "height": None,
        "mode": None,
        "sha256": None,
        "status": None,
        "duplicate_of": None,
        "staged_relative_path": None,
        "warnings": [],
    }


def run_local_image_intake(
    source_dir: Path,
    output_dir: Path,
    *,
    recursive: bool = True,
    copy_unique: bool = True,
) -> Dict[str, Any]:
    """Scan ``source_dir`` and write deterministic design-learning artifacts.

    Originals are never moved, modified, or deleted. The lexicographically
    first path owns an exact SHA-256 digest; later exact matches point to it.
    """
    source_root = Path(source_dir).expanduser().resolve()
    output_root = Path(output_dir).expanduser().resolve()
    manifest_path = output_root / "local_image_manifest.json"
    contact_sheet_path = output_root / "contact_sheet.png"
    unique_dir = output_root / "unique"
    warnings: List[str] = []
    entries: List[Dict[str, Any]] = []

    if not source_root.is_dir():
        warnings.append("source_directory_missing")
        paths: List[Path] = []
    else:
        iterator = source_root.rglob("*") if recursive else source_root.glob("*")
        paths = []
        for path in iterator:
            try:
                resolved = path.resolve()
                if not path.is_file() or _is_below(resolved, output_root):
                    continue
                if not _is_below(resolved, source_root):
                    warnings.append("outside_source_skipped")
                    continue
                paths.append(path)
            except OSError:
                warnings.append("path_unreadable")
        paths.sort(key=lambda item: item.relative_to(source_root).as_posix().casefold())

    digest_owner: Dict[str, Dict[str, Any]] = {}
    for path in paths:
        entry = _base_entry(path, source_root)
        try:
            entry["size_bytes"] = path.stat().st_size
        except OSError:
            entry["status"] = "unreadable"
            entry["warnings"].append("stat_failed")
            entries.append(entry)
            continue

        if entry["extension"] not in SUPPORTED_EXTENSIONS:
            entry["status"] = "unsupported"
            entry["warnings"].append("unsupported_extension")
            entries.append(entry)
            continue

        try:
            digest = _sha256(path)
            width, height, mode = _inspect_image(path)
        except Exception as error:
            entry["status"] = "unreadable"
            entry["warnings"].append(f"image_read_error:{type(error).__name__}")
            entries.append(entry)
            continue

        asset_id = f"sha256:{digest}"
        entry.update({
            "asset_id": asset_id,
            "sha256": digest,
            "width": width,
            "height": height,
            "mode": mode,
        })
        owner = digest_owner.get(digest)
        if owner is not None:
            entry["status"] = "exact_duplicate"
            entry["duplicate_of"] = owner["asset_id"]
            entries.append(entry)
            continue

        entry["status"] = "unique"
        digest_owner[digest] = entry
        if copy_unique:
            staged_name = f"{digest[:16]}_{path.name}"
            staged_path = unique_dir / staged_name
            try:
                unique_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, staged_path)
                entry["staged_relative_path"] = staged_path.relative_to(output_root).as_posix()
            except OSError as error:
                entry["warnings"].append(f"staging_error:{type(error).__name__}")
                warnings.append("staging_failed")
        entries.append(entry)

    contact_sheet = generate_contact_sheet(
        entries, output_root, contact_sheet_path
    ) if copy_unique else {
        "status": "skipped",
        "image_count": 0,
        "columns": 4,
        "rows": 0,
        "included_asset_ids": [],
        "warnings": ["unique_staging_disabled"],
    }
    if contact_sheet["status"] == "failed":
        warnings.extend(contact_sheet.get("warnings", []))

    counts = {
        "discovered_count": len(paths),
        "supported_count": sum(
            entry["status"] not in {"unsupported"} for entry in entries
        ),
        "unique_count": sum(entry["status"] == "unique" for entry in entries),
        "exact_duplicate_count": sum(
            entry["status"] == "exact_duplicate" for entry in entries
        ),
        "unreadable_count": sum(entry["status"] == "unreadable" for entry in entries),
        "unsupported_count": sum(entry["status"] == "unsupported" for entry in entries),
    }
    if counts["unreadable_count"] or counts["unsupported_count"]:
        warnings.append("some_files_not_ingested")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "completed_with_warnings" if warnings else "completed",
        "generated_at": datetime.now().isoformat(),
        "source_root": "local_source",
        "output_root": "intake_output",
        "path_policy": {
            "root_values": "opaque_local_markers",
            "file_paths": "relative_to_local_source",
            "staged_paths": "relative_to_intake_output",
            "absolute_paths_persisted": False,
        },
        "scan": counts,
        "files": entries,
        "outputs": {
            "manifest_path": manifest_path.name,
            "contact_sheet_path": contact_sheet_path.name,
            "unique_dir": unique_dir.name,
        },
        "contact_sheet": contact_sheet,
        "warnings": warnings,
    }
    try:
        _write_json_atomic(manifest_path, payload)
    except OSError as error:
        payload["status"] = "completed_with_warnings"
        payload["warnings"].append(f"manifest_write_error:{type(error).__name__}")
    return payload
