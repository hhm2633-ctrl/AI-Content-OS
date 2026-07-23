"""Owner-source screenshot batching and approved fixed-layout learning.

Raw screenshots stay immutable under the owner-provided source directory.  This
module prepares deterministic batches of at most ten images, validates rich
human/AI analysis records, and compiles only explicitly owner-approved records
into a lightweight runtime layout-profile registry.

Screenshot observations are reference evidence, never Instagram performance.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from PIL import Image, ImageOps


BATCH_SCHEMA_VERSION = "owner_source_batch_v1"
ANALYSIS_SCHEMA_VERSION = "owner_source_design_analysis_v1"
REGISTRY_SCHEMA_VERSION = "approved_layout_registry_v1"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
ACCOUNT_IDS = {
    "account_a",
    "account_b",
    "account_c",
    "shared",
    "news",
    "story",
    "fashion",
    "beauty",
}
MAX_APPROVED_REFERENCE_PROFILES = 40
REQUIRED_ANALYSIS_SECTIONS = (
    "context",
    "design",
    "palette",
    "typography",
    "content_insight",
    "recommendation",
    "approval",
)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _string_list(value: Any, *, limit: int = 30) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [_text(item) for item in value if _text(item)][:limit]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _source_assets(source_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    if not source_root.is_dir():
        return [], ["source_directory_missing"]
    paths = sorted(
        (
            path
            for path in source_root.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ),
        key=lambda path: path.relative_to(source_root).as_posix().casefold(),
    )
    assets: list[dict[str, Any]] = []
    digest_owner: dict[str, str] = {}
    for path in paths:
        relative_path = path.relative_to(source_root).as_posix()
        try:
            digest = _sha256(path)
            with Image.open(path) as opened:
                image = ImageOps.exif_transpose(opened)
                width, height = image.size
        except Exception as error:
            warnings.append(f"unreadable:{relative_path}:{type(error).__name__}")
            continue
        if digest in digest_owner:
            warnings.append(f"exact_duplicate:{relative_path}:{digest_owner[digest]}")
            continue
        asset_id = f"sha256:{digest}"
        digest_owner[digest] = relative_path
        assets.append(
            {
                "asset_id": asset_id,
                "source_relative_path": relative_path,
                "size_bytes": path.stat().st_size,
                "width": width,
                "height": height,
                "extension": path.suffix.lower(),
                "source_role": "owner_reference_screenshot",
                "is_performance_evidence": False,
            }
        )
    return assets, warnings


def _analysis_template(asset: Mapping[str, Any], batch_id: str) -> dict[str, Any]:
    return {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "asset_id": asset["asset_id"],
        "batch_id": batch_id,
        "source_relative_path": asset["source_relative_path"],
        "analysis_status": "PENDING",
        "evidence_boundary": {
            "source": "owner_source_screenshot",
            "is_performance_evidence": False,
            "reference_only": True,
        },
        "context": {
            "account_targets": [],
            "content_categories": [],
            "issue_types": [],
            "moods": [],
            "emotional_arc": [],
            "seasonality": [],
            "media_conditions": [],
        },
        "design": {
            "composition": "",
            "layout_structure": "",
            "visual_hierarchy": "",
            "image_strategy": "",
            "text_density": "",
            "spacing": "",
            "decorative_elements": [],
            "carousel_consistency": "",
        },
        "palette": {
            "dominant_colors": [],
            "accent_colors": [],
            "background_tone": "",
            "contrast_style": "",
            "color_relationship": "",
        },
        "typography": {
            "headline_style": "",
            "body_style": "",
            "alignment": "",
            "emphasis_method": "",
            "readability_notes": "",
        },
        "content_insight": {
            "topic_summary": "",
            "body_structure": "",
            "claims_or_information": [],
            "hook_style": "",
            "cta_style": "",
            "project_help": [],
            "reusable_rules": [],
            "do_not_copy": [],
        },
        "recommendation": {
            "profile_id": "",
            "fixed_layout_id": "",
            "reference_scope": "shared",
            "usage_conditions": [],
            "adaptation_notes": [],
            "style_overrides": {},
            "layout_blueprint": {
                "canvas_structure": "",
                "image_zones": [],
                "text_zones": [],
                "reading_order": [],
                "repeating_elements": [],
                "role_variants": {},
            },
        },
        "approval": {
            "status": "CANDIDATE",
            "approved_by": "",
            "approved_at": "",
            "owner_feedback_event_id": "",
        },
    }


def prepare_owner_source_batches(
    source_dir: str | Path,
    workspace_dir: str | Path,
    *,
    batch_size: int = 10,
) -> dict[str, Any]:
    """Prepare manifests/templates without moving, copying, or editing sources."""

    if not isinstance(batch_size, int) or batch_size < 1 or batch_size > 10:
        raise ValueError("batch_size must be between 1 and 10")
    source_root = Path(source_dir).expanduser().resolve()
    workspace_root = Path(workspace_dir).expanduser().resolve()
    assets, warnings = _source_assets(source_root)
    batches: list[dict[str, Any]] = []
    for offset in range(0, len(assets), batch_size):
        items = assets[offset : offset + batch_size]
        ordinal = offset // batch_size + 1
        fingerprint = hashlib.sha256(
            "|".join(item["asset_id"] for item in items).encode("utf-8")
        ).hexdigest()[:12]
        batch_id = f"batch_{ordinal:04d}_{fingerprint}"
        batch_dir = workspace_root / "batches" / batch_id
        manifest = {
            "schema_version": BATCH_SCHEMA_VERSION,
            "batch_id": batch_id,
            "batch_order": ordinal,
            "asset_count": len(items),
            "max_asset_count": 10,
            "source_root": "owner_source",
            "source_files_modified": False,
            "is_performance_evidence": False,
            "analysis_scope": [
                "context",
                "design_layout",
                "palette_color_matching",
                "typography",
                "carousel_and_body_style",
                "content_insight",
                "project_help",
            ],
            "assets": items,
        }
        template = {
            "schema_version": ANALYSIS_SCHEMA_VERSION,
            "batch_id": batch_id,
            "records": [_analysis_template(item, batch_id) for item in items],
        }
        _atomic_json(batch_dir / "manifest.json", manifest)
        analysis_path = batch_dir / "analysis.json"
        if not analysis_path.exists():
            _atomic_json(analysis_path, template)
        batches.append(
            {
                "batch_id": batch_id,
                "asset_count": len(items),
                "manifest_relative_path": (batch_dir / "manifest.json").relative_to(workspace_root).as_posix(),
                "analysis_relative_path": analysis_path.relative_to(workspace_root).as_posix(),
            }
        )
    index = {
        "schema_version": BATCH_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_root": "owner_source",
        "workspace_root": "design_learning_workspace",
        "path_policy": {"absolute_paths_persisted": False, "source_files_modified": False},
        "batch_size": batch_size,
        "unique_asset_count": len(assets),
        "batch_count": len(batches),
        "batches": batches,
        "warnings": warnings,
    }
    _atomic_json(workspace_root / "batch_index.json", index)
    return index


def validate_analysis_record(
    record: Mapping[str, Any],
    *,
    allowed_layout_ids: Sequence[str],
) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, Mapping):
        return ["record_not_object"]
    asset_id = _text(record.get("asset_id"))
    if not asset_id.startswith("sha256:"):
        errors.append("invalid_asset_id")
    if record.get("schema_version") != ANALYSIS_SCHEMA_VERSION:
        errors.append("invalid_schema_version")
    for section in REQUIRED_ANALYSIS_SECTIONS:
        if not isinstance(record.get(section), Mapping):
            errors.append(f"missing_section:{section}")
    boundary = record.get("evidence_boundary")
    if not isinstance(boundary, Mapping) or boundary.get("is_performance_evidence") is not False:
        errors.append("performance_boundary_missing")
    context = record.get("context") if isinstance(record.get("context"), Mapping) else {}
    unknown_accounts = set(_string_list(context.get("account_targets"))) - ACCOUNT_IDS
    if unknown_accounts:
        errors.append(f"unknown_accounts:{','.join(sorted(unknown_accounts))}")
    recommendation = (
        record.get("recommendation") if isinstance(record.get("recommendation"), Mapping) else {}
    )
    fixed_layout_id = _text(recommendation.get("fixed_layout_id"))
    if fixed_layout_id and fixed_layout_id not in set(allowed_layout_ids):
        errors.append(f"unknown_fixed_layout:{fixed_layout_id}")
    approval = record.get("approval") if isinstance(record.get("approval"), Mapping) else {}
    status = _text(approval.get("status")) or "CANDIDATE"
    if status not in {"CANDIDATE", "OWNER_APPROVED", "REJECTED"}:
        errors.append(f"invalid_approval_status:{status}")
    if status == "OWNER_APPROVED":
        if _text(approval.get("approved_by")) != "owner":
            errors.append("owner_approval_identity_missing")
        if not _text(approval.get("approved_at")):
            errors.append("owner_approval_time_missing")
        if not fixed_layout_id:
            errors.append("approved_record_missing_fixed_layout")
        if not _text(recommendation.get("profile_id")):
            errors.append("approved_record_missing_profile_id")
    return errors


def _profile_from_record(record: Mapping[str, Any]) -> dict[str, Any]:
    context = dict(record.get("context") or {})
    recommendation = dict(record.get("recommendation") or {})
    approval = dict(record.get("approval") or {})
    return {
        "profile_id": _text(recommendation.get("profile_id")),
        "base_layout_id": _text(recommendation.get("fixed_layout_id")),
        "source_asset_id": _text(record.get("asset_id")),
        "source_batch_id": _text(record.get("batch_id")),
        "account_targets": _string_list(context.get("account_targets")),
        "content_categories": _string_list(context.get("content_categories")),
        "issue_types": _string_list(context.get("issue_types")),
        "moods": _string_list(context.get("moods")),
        "emotional_arc": _string_list(context.get("emotional_arc")),
        "seasonality": _string_list(context.get("seasonality")),
        "media_conditions": _string_list(context.get("media_conditions")),
        "usage_conditions": _string_list(recommendation.get("usage_conditions")),
        "adaptation_notes": _string_list(recommendation.get("adaptation_notes")),
        "style_overrides": dict(recommendation.get("style_overrides") or {}),
        "layout_blueprint": dict(recommendation.get("layout_blueprint") or {}),
        "reference_scope": _text(recommendation.get("reference_scope")) or "shared",
        "owner_approval": {
            "approved_by": "owner",
            "approved_at": _text(approval.get("approved_at")),
            "owner_feedback_event_id": _text(approval.get("owner_feedback_event_id")),
        },
        "is_performance_evidence": False,
    }


def compile_approved_layout_registry(
    records: Iterable[Mapping[str, Any]],
    *,
    allowed_layout_ids: Sequence[str],
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Compile valid owner-approved profiles; candidates never enter runtime."""

    profiles: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen_profiles: set[str] = set()
    for record in records:
        errors = validate_analysis_record(record, allowed_layout_ids=allowed_layout_ids)
        approval = record.get("approval") if isinstance(record, Mapping) else {}
        if not isinstance(approval, Mapping) or approval.get("status") != "OWNER_APPROVED":
            continue
        profile_id = _text((record.get("recommendation") or {}).get("profile_id"))
        if profile_id in seen_profiles:
            errors.append(f"duplicate_profile_id:{profile_id}")
        if errors:
            rejected.append({"asset_id": _text(record.get("asset_id")), "errors": errors})
            continue
        if len(profiles) >= MAX_APPROVED_REFERENCE_PROFILES:
            rejected.append(
                {
                    "asset_id": _text(record.get("asset_id")),
                    "errors": ["approved_reference_profile_capacity_exceeded:40"],
                }
            )
            continue
        seen_profiles.add(profile_id)
        profiles.append(_profile_from_record(record))
    registry = {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "learning_boundary": {
            "owner_approval_required": True,
            "screenshot_observation_is_performance": False,
            "runtime_uses_candidates": False,
        },
        "allowed_layout_ids": list(allowed_layout_ids),
        "reference_pool_scope": "shared_account_a_b_c",
        "max_approved_profile_count": MAX_APPROVED_REFERENCE_PROFILES,
        "approved_profile_count": len(profiles),
        "rejected_approved_record_count": len(rejected),
        "profiles": profiles,
        "rejected_records": rejected,
    }
    if output_path is not None:
        _atomic_json(Path(output_path), registry)
    return registry


def load_analysis_records(workspace_dir: str | Path) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for path in sorted(Path(workspace_dir).glob("batches/*/analysis.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"analysis_read_failed:{path.name}:{type(error).__name__}")
            continue
        batch_records = payload.get("records") if isinstance(payload, Mapping) else None
        if not isinstance(batch_records, list):
            errors.append(f"analysis_records_missing:{path.parent.name}")
            continue
        records.extend(item for item in batch_records if isinstance(item, dict))
    return records, errors


__all__ = [
    "ANALYSIS_SCHEMA_VERSION",
    "BATCH_SCHEMA_VERSION",
    "REGISTRY_SCHEMA_VERSION",
    "MAX_APPROVED_REFERENCE_PROFILES",
    "compile_approved_layout_registry",
    "load_analysis_records",
    "prepare_owner_source_batches",
    "validate_analysis_record",
]
