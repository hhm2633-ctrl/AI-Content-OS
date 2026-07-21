"""CLI wrapper to run local image intake on a single batch directory."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from modules.design_learning.local_image_intake import run_local_image_intake


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    source_dir = args.source_dir
    output_dir = args.output_dir

    result = run_local_image_intake(source_dir=source_dir, output_dir=output_dir)
    output_root = output_dir.resolve()
    manifest_path = output_root / "local_image_manifest.json"
    manifest_alias_path = output_root / "manifest.json"
    contact_sheet_path = output_root / "contact_sheet.png"

    if manifest_path.exists():
        shutil.copy2(manifest_path, manifest_alias_path)

    print(json.dumps({
        "status": "completed",
        "source_dir": str(source_dir),
        "output_dir": str(output_root),
        "manifest_path": str(manifest_path),
        "manifest_json_path": str(manifest_alias_path),
        "contact_sheet_path": str(contact_sheet_path),
        "manifest_exists": manifest_path.exists(),
        "manifest_json_exists": manifest_alias_path.exists(),
        "contact_sheet_exists": contact_sheet_path.exists(),
        "discovered_count": result.get("scan", {}).get("discovered_count"),
        "supported_count": result.get("scan", {}).get("supported_count"),
        "unique_count": result.get("scan", {}).get("unique_count"),
        "exact_duplicate_count": result.get("scan", {}).get("exact_duplicate_count"),
        "warnings": result.get("warnings", []),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
