"""Fail-closed, read-only verification for CardNews production packages.

This command intentionally imports only Python's standard library and only reads
``latest.json`` plus sibling candidate JSON files.  It does not build packages,
run WorkflowEngine, generate/render media, publish, issue links, call a network,
or invoke Git.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = REPO_ROOT / "artifacts" / "cardnews_production_packages" / "latest.json"
INDEX_SCHEMA = "cardnews_production_package_index_v1"
PACKAGE_SCHEMA = "selected_candidate_production_package_v1"
READY_STATUS = "production_package_ready"
ALLOWED_STATUSES = {READY_STATUS, "blocked"}


def _nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return bool(value)
    if isinstance(value, list):
        return bool(value)
    return value is not None


def _load_object(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"JSON object required: {path.name}")
    return value


def _package_path(index_path: Path, candidate_id: str) -> Path:
    # Candidate files are deliberately constrained to siblings of latest.json.
    # This prevents a crafted manifest from making verification read elsewhere.
    if not candidate_id or candidate_id in {".", ".."}:
        raise ValueError("candidate_id_missing")
    if Path(candidate_id).name != candidate_id or any(ch in candidate_id for ch in ("/", "\\")):
        raise ValueError(f"candidate_id_path_rejected:{candidate_id}")
    return index_path.parent / f"{candidate_id}.json"


def _execution_errors(package: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    receipts = package.get("receipts")
    receipts = receipts if isinstance(receipts, Mapping) else {}
    if receipts.get("package_only") is not True:
        errors.append("receipt_package_only_not_true")
    for field in ("render_executed", "publish_executed", "link_issuance_executed"):
        if receipts.get(field) is not False:
            errors.append(f"receipt_{field}_not_false")

    gates = package.get("gates")
    gates = gates if isinstance(gates, Mapping) else {}
    for gate_name in ("render", "publish"):
        gate = gates.get(gate_name)
        gate = gate if isinstance(gate, Mapping) else {}
        if gate.get("authorized") is not False or gate.get("status") != "blocked":
            errors.append(f"{gate_name}_gate_not_blocked")
    return errors


def _ready_errors(package: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    required = {
        "story": package.get("story"),
        "slides": package.get("slides"),
        "feed_caption": package.get("feed_caption"),
        "media_plan": package.get("media_plan"),
    }
    for field, value in required.items():
        if not _nonempty(value):
            errors.append(f"ready_{field}_missing")
    slides = package.get("slides")
    media_plan = package.get("media_plan")
    if isinstance(slides, list) and isinstance(media_plan, list) and len(slides) != len(media_plan):
        errors.append("ready_slide_media_count_mismatch")
    quality = package.get("quality_receipt")
    quality = quality if isinstance(quality, Mapping) else {}
    if quality.get("schema_version") != "cardnews_package_content_quality_gate_v1":
        errors.append("ready_quality_receipt_missing")
    elif quality.get("quality_passed") is not True:
        errors.append("ready_content_quality_not_passed")
    return errors


def verify_package_index(index_path: Path = DEFAULT_INDEX) -> Dict[str, Any]:
    """Read and verify one package index without executing any project behavior."""
    index_path = index_path.resolve()
    errors: List[str] = []
    checked = 0
    ready = 0
    blocked = 0

    try:
        manifest = _load_object(index_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "status": "failed",
            "package_only": True,
            "checked_count": 0,
            "errors": [f"index_unreadable:{exc}"],
        }

    if manifest.get("schema_version") != INDEX_SCHEMA:
        errors.append("index_schema_invalid")
    for field in ("render_executed", "publish_executed", "link_issuance_executed"):
        if manifest.get(field) is not False:
            errors.append(f"index_{field}_not_false")

    entries = manifest.get("packages")
    if not isinstance(entries, list):
        entries = []
        errors.append("index_packages_invalid")

    seen = set()
    for entry in entries:
        if not isinstance(entry, Mapping):
            errors.append("index_entry_invalid")
            continue
        candidate_id = str(entry.get("candidate_id") or "").strip()
        if candidate_id in seen:
            errors.append(f"duplicate_candidate:{candidate_id}")
            continue
        seen.add(candidate_id)
        try:
            package_path = _package_path(index_path, candidate_id)
            package = _load_object(package_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"package_unreadable:{candidate_id}:{exc}")
            continue

        checked += 1
        if package.get("schema_version") != PACKAGE_SCHEMA:
            errors.append(f"package_schema_invalid:{candidate_id}")
        package_candidate = package.get("candidate")
        package_candidate = package_candidate if isinstance(package_candidate, Mapping) else {}
        if str(package_candidate.get("candidate_id") or "") != candidate_id:
            errors.append(f"candidate_mismatch:{candidate_id}")
        if package.get("status") != entry.get("status"):
            errors.append(f"status_mismatch:{candidate_id}")
        status = package.get("status")
        if status not in ALLOWED_STATUSES:
            errors.append(f"status_invalid:{candidate_id}")
        elif status == READY_STATUS:
            ready += 1
            errors.extend(f"{candidate_id}:{item}" for item in _ready_errors(package))
        else:
            blocked += 1
            if not _nonempty(package.get("reason_code")):
                errors.append(f"blocked_reason_missing:{candidate_id}")
        errors.extend(f"{candidate_id}:{item}" for item in _execution_errors(package))

    expected = manifest.get("package_count")
    if expected != len(entries) or checked != len(entries):
        errors.append("package_count_mismatch")
    if manifest.get("ready_count") != ready or manifest.get("blocked_count") != blocked:
        errors.append("status_count_mismatch")

    return {
        "status": "passed" if not errors else "failed",
        "package_only": True,
        "index_path": str(index_path),
        "checked_count": checked,
        "ready_count": ready,
        "blocked_count": blocked,
        "errors": errors,
        "execution": {
            "workflow": False,
            "generation": False,
            "render": False,
            "publish": False,
            "link_issuance": False,
            "external_calls": False,
            "git": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    args = parser.parse_args()
    receipt = verify_package_index(args.index)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
