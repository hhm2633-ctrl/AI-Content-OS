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


DEFAULT_SOURCE = Path("F:/AI-Content-OS-Data/owner_source")


def _default_workspace() -> Path:
    return resolve_external_path("artifacts", "design_learning", "owner_source", create=True)


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
    args = parser.parse_args()
    workspace = args.workspace_dir or _default_workspace()
    if args.command == "prepare":
        result = prepare_owner_source_batches(args.source_dir, workspace, batch_size=args.batch_size)
    else:
        records, read_errors = load_analysis_records(workspace)
        output_path = workspace / "approved_layout_registry.json"
        result = compile_approved_layout_registry(
            records,
            allowed_layout_ids=load_layout_ids(str(args.layout_rules)),
            output_path=output_path,
        )
        result["analysis_read_errors"] = read_errors
        result["registry_path"] = str(output_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
