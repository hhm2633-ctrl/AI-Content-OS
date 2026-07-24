"""Prepare owner-source batches or compile approved fixed-layout profiles."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from modules.common.external_storage import resolve_external_path
from modules.design_learning.card_news_design_learning import load_layout_ids
from modules.design_learning.owner_source_learning import (
    compile_approved_layout_registry,
    load_analysis_records,
    prepare_owner_source_batches,
)
from modules.design_learning.reference_specimen_registry import (
    audit_existing_reference_v2_material,
    build_reference_v2_registry,
)
from modules.design_learning.reference_geometry_draft_builder import (
    build_reference_geometry_draft_batch,
)


DEFAULT_SOURCE = Path("F:/AI-Content-OS-Data/owner_source")
DEFAULT_TAXONOMY = (
    REPOSITORY_ROOT
    / "knowledge"
    / "owner_feedback"
    / "owner_learning_taxonomy_v1.json"
)
DEFAULT_CANDIDATE_EVIDENCE = Path(
    "F:/AI-Content-OS-Data/artifacts/design_learning/"
    "reference_candidate_evidence_20260724.json"
)
DEFAULT_GEOMETRY_DRAFT_OUTPUT = Path(
    "F:/AI-Content-OS-Data/artifacts/design_learning/"
    "reference_geometry_cropped_drafts_rework_20260724"
)


def _default_workspace() -> Path:
    return resolve_external_path("artifacts", "design_learning", "owner_source", create=True)


def audit_existing_reference_v2(
    *,
    source_dir: Path,
    taxonomy_path: Path,
    repository_root: Path = REPOSITORY_ROOT,
) -> dict:
    taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    if not isinstance(taxonomy, dict):
        raise ValueError("owner learning taxonomy must be an object")
    return audit_existing_reference_v2_material(
        source_root=source_dir,
        taxonomy_payload=taxonomy,
        repository_root=repository_root,
    )


def draft_existing_reference_v2_geometry(
    *,
    candidate_evidence_path: Path,
    source_dir: Path,
    output_dir: Path,
    timeout_seconds: float = 120.0,
    ocr_extractor=None,
) -> dict:
    payload = json.loads(candidate_evidence_path.read_text(encoding="utf-8"))
    kwargs = {
        "source_root": source_dir,
        "output_dir": output_dir,
        "timeout_seconds": timeout_seconds,
    }
    if ocr_extractor is not None:
        kwargs["ocr_extractor"] = ocr_extractor
    return build_reference_geometry_draft_batch(
        payload,
        **kwargs,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    prepare.add_argument("--workspace-dir", type=Path, default=None)
    prepare.add_argument("--batch-size", type=int, default=10)
    compile_parser = subparsers.add_parser("compile")
    compile_parser.add_argument("--workspace-dir", type=Path, default=None)
    compile_parser.add_argument(
        "--layout-rules", type=Path, default=REPOSITORY_ROOT / "templates" / "card_news_layout_rules.json"
    )
    reference_parser = subparsers.add_parser("compile-reference-v2")
    reference_parser.add_argument("--specimens-json", type=Path, required=True)
    reference_parser.add_argument("--blueprints-json", type=Path, required=True)
    reference_parser.add_argument("--output", type=Path, default=None)
    audit_parser = subparsers.add_parser("audit-reference-v2")
    audit_parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    audit_parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    audit_parser.add_argument("--summary-only", action="store_true")
    draft_parser = subparsers.add_parser("draft-reference-v2-geometry")
    draft_parser.add_argument(
        "--candidate-evidence",
        type=Path,
        default=DEFAULT_CANDIDATE_EVIDENCE,
    )
    draft_parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    draft_parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_GEOMETRY_DRAFT_OUTPUT,
    )
    draft_parser.add_argument("--timeout-seconds", type=float, default=120.0)
    args = parser.parse_args()
    if args.command == "prepare":
        workspace = args.workspace_dir or _default_workspace()
        result = prepare_owner_source_batches(args.source_dir, workspace, batch_size=args.batch_size)
    elif args.command == "compile":
        workspace = args.workspace_dir or _default_workspace()
        records, read_errors = load_analysis_records(workspace)
        output_path = workspace / "approved_layout_registry.json"
        result = compile_approved_layout_registry(
            records,
            allowed_layout_ids=load_layout_ids(str(args.layout_rules)),
            output_path=output_path,
        )
        result["analysis_read_errors"] = read_errors
        result["registry_path"] = str(output_path)
    elif args.command == "compile-reference-v2":
        workspace = _default_workspace()
        specimens_payload = json.loads(args.specimens_json.read_text(encoding="utf-8"))
        blueprints_payload = json.loads(args.blueprints_json.read_text(encoding="utf-8"))
        specimens = (
            specimens_payload.get("specimens", [])
            if isinstance(specimens_payload, dict)
            else specimens_payload
        )
        blueprints = (
            blueprints_payload.get("blueprints", {})
            if isinstance(blueprints_payload, dict)
            else blueprints_payload
        )
        result = build_reference_v2_registry(specimens, blueprints)
        output_path = args.output or workspace / "approved_reference_v2_registry.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        result["registry_path"] = str(output_path)
    elif args.command == "audit-reference-v2":
        result = audit_existing_reference_v2(
            source_dir=args.source_dir,
            taxonomy_path=args.taxonomy,
        )
    else:
        result = draft_existing_reference_v2_geometry(
            candidate_evidence_path=args.candidate_evidence,
            source_dir=args.source_dir,
            output_dir=args.output_dir,
            timeout_seconds=args.timeout_seconds,
        )
    printed = result
    if getattr(args, "summary_only", False):
        printed = {
            key: result[key]
            for key in (
                "schema_version",
                "status",
                "source_inventory",
                "analysis_inventory",
                "required_inputs",
                "blockers",
                "intermediate_artifact",
                "selectable_reference_ids",
                "auto_approval_performed",
                "external_write_performed",
            )
        }
    print(json.dumps(printed, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "audit_existing_reference_v2",
    "draft_existing_reference_v2_geometry",
    "main",
]
