"""Integrate account repair inputs and run a bounded package-only quality loop."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.card_news.package_content_quality_gate import assess_package_content_quality  # noqa: E402


DEFAULT_PACKAGE_ROOT = REPO_ROOT / "artifacts" / "cardnews_production_packages"
DEFAULT_REPAIR_ROOT = DEFAULT_PACKAGE_ROOT / "repair_inputs"
DEFAULT_REVIEW_ROOT = DEFAULT_PACKAGE_ROOT / "repair_reviews"
SCHEMA_VERSION = "cardnews_package_quality_loop_v1"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _records(root: Path) -> List[Mapping[str, Any]]:
    records: List[Mapping[str, Any]] = []
    for account in ("A", "B", "C"):
        path = root / f"account_{account}.json"
        if not path.exists():
            continue
        value = _load(path)
        rows = value.get("records") if isinstance(value, Mapping) else []
        records.extend(item for item in rows if isinstance(item, Mapping))
    return records


def _reviews(root: Path) -> Dict[str, Mapping[str, Any]]:
    indexed: Dict[str, Mapping[str, Any]] = {}
    for account in ("A", "B", "C"):
        path = root / f"review_{account}.json"
        if not path.exists():
            continue
        value = _load(path)
        rows = value.get("records") if isinstance(value, Mapping) else []
        for item in rows if isinstance(rows, list) else []:
            if isinstance(item, Mapping) and str(item.get("candidate_id") or "").strip():
                indexed[str(item["candidate_id"]).strip()] = item
    return indexed


def _latest_review_cycle(root: Path) -> int:
    cycles: List[int] = []
    for account in ("A", "B", "C"):
        path = root / f"review_{account}.json"
        if not path.exists():
            continue
        value = _load(path)
        cycle = value.get("cycle") if isinstance(value, Mapping) else None
        if isinstance(cycle, int) and cycle > 0:
            cycles.append(cycle)
    return max(cycles, default=0)


def _normalize_record(record: Mapping[str, Any]) -> Dict[str, Any]:
    value = copy.deepcopy(dict(record))
    slides = value.get("slides") if isinstance(value.get("slides"), list) else []
    media = value.get("media_plan") if isinstance(value.get("media_plan"), list) else []
    for page, slide in enumerate(slides, start=1):
        if isinstance(slide, dict):
            slide["page"] = page
            slide.setdefault("role", "cover" if page == 1 else "source_context")
    for page, item in enumerate(media, start=1):
        if not isinstance(item, dict):
            continue
        item["page"] = page
        if page <= len(slides) and isinstance(slides[page - 1], Mapping):
            item.setdefault("slide_role", slides[page - 1].get("role") or "source_context")
        credit = item.get("source_credit")
        if isinstance(credit, str) and credit.strip():
            item["source_credit"] = [credit.strip()]
    value["slides"] = slides
    value["media_plan"] = media
    value["slide_count"] = len(slides)
    return value


def _package(record: Mapping[str, Any]) -> Dict[str, Any]:
    candidate_id = str(record.get("candidate_id") or "").strip()
    account = str(record.get("account") or "").strip().upper()
    category = str(record.get("category") or "").strip()
    title = str(record.get("title") or "").strip()
    evidence = record.get("evidence") if isinstance(record.get("evidence"), Mapping) else {}
    story = record.get("story") if isinstance(record.get("story"), Mapping) else {}
    source_gates = record.get("gates") if isinstance(record.get("gates"), Mapping) else {}
    source_approval = source_gates.get("package_approval") if isinstance(source_gates.get("package_approval"), Mapping) else {}
    approval_valid = (
        source_approval.get("status") == "approved"
        and source_approval.get("approved") is True
        and str(source_approval.get("scope") or "").strip() == "production_package"
        and str(source_approval.get("candidate_id") or "").strip() == candidate_id
        and bool(str(source_approval.get("approved_by") or "").strip())
        and bool(str(source_approval.get("receipt_id") or "").strip())
    )
    source_status = str(record.get("status") or "").strip()
    if source_status == "blocked":
        package_status = "blocked"
    elif source_status == "production_package_ready" and approval_valid:
        package_status = "production_package_ready"
    else:
        package_status = "production_package_pending_approval"
    package_reason = str(record.get("reason_code") or "").strip()
    if package_status == "production_package_pending_approval":
        package_reason = "package_approval_required"
    return {
        "schema_version": "selected_candidate_production_package_v1",
        "package_id": f"cardnews-package:{candidate_id}",
        "status": package_status,
        "reason_code": package_reason or "quality_loop_candidate",
        "candidate": {"candidate_id": candidate_id, "account": account, "category": category, "title": title},
        "evidence": copy.deepcopy(dict(evidence)),
        "story": copy.deepcopy(dict(story)),
        "slide_count": record.get("slide_count"),
        "slides": copy.deepcopy(record.get("slides", [])),
        "feed_caption": str(record.get("feed_caption") or "").strip(),
        "media_plan": copy.deepcopy(record.get("media_plan", [])),
        "commerce": copy.deepcopy(record.get("commerce")) if isinstance(record.get("commerce"), Mapping) else None,
        "quality_notes": copy.deepcopy(record.get("quality_notes")) if isinstance(record.get("quality_notes"), Mapping) else {},
        "gates": {
            "package_approval": (
                copy.deepcopy(dict(source_approval))
                if approval_valid
                else {
                    "status": "pending",
                    "approved": False,
                    "scope": "production_package",
                    "reason_code": "package_approval_required",
                }
            ),
            "render": {"status": "blocked", "authorized": False, "reason_code": "separate_render_approval_required"},
            "publish": {"status": "blocked", "authorized": False, "reason_code": "separate_publish_approval_required"},
        },
        "receipts": {"package_only": True, "render_executed": False, "publish_executed": False, "link_issuance_executed": False},
    }


def run_quality_loop(
    repair_root: Path = DEFAULT_REPAIR_ROOT,
    package_root: Path = DEFAULT_PACKAGE_ROOT,
    max_cycles: int = 10,
    review_root: Path | None = None,
) -> Dict[str, Any]:
    if not 1 <= max_cycles <= 10:
        raise ValueError("max_cycles must be between 1 and 10")
    records = _records(repair_root)
    resolved_review_root = review_root or (package_root / "repair_reviews")
    review_index = _reviews(resolved_review_root)
    editorial_cycles = _latest_review_cycle(resolved_review_root)
    packages: Dict[str, Dict[str, Any]] = {}
    existing = _load(package_root / "latest.json") if (package_root / "latest.json").exists() else {"packages": []}
    prior_loop = existing.get("quality_loop") if isinstance(existing, Mapping) else {}
    prior_receipts = prior_loop.get("receipts") if isinstance(prior_loop, Mapping) else []
    cycle_receipts: List[Dict[str, Any]] = copy.deepcopy(prior_receipts) if isinstance(prior_receipts, list) else []
    first_cycle = len(cycle_receipts) + 1

    normalized = [_normalize_record(record) for record in records]
    for cycle in range(first_cycle, max_cycles + 1):
        failures: List[Dict[str, Any]] = []
        packages = {}
        for record in normalized:
            package = _package(record)
            quality = assess_package_content_quality(package)
            independent = review_index.get(package["candidate"]["candidate_id"])
            if isinstance(independent, Mapping):
                quality["independent_review"] = copy.deepcopy(dict(independent))
                if str(independent.get("decision") or "").lower() != "pass":
                    quality["quality_passed"] = False
                    quality["status"] = "repair_required"
                    quality["failures"].append(
                        {
                            "field": "independent_review",
                            "reason_code": "independent_review_revise",
                            "detail": " | ".join(
                                str(item) for item in independent.get("issues", []) if str(item).strip()
                            ) or "independent reviewer requested revision",
                        }
                    )
                    quality["failure_count"] = len(quality["failures"])
            package["quality_receipt"] = quality
            if not quality["quality_passed"]:
                if package["status"] == "production_package_ready":
                    package["status"] = "blocked"
                    package["reason_code"] = "content_quality_repair_required"
                package["missing_requirements"] = [item["reason_code"] for item in quality["failures"]]
                failures.append({"candidate_id": package["candidate"]["candidate_id"], "failures": quality["failures"]})
            packages[package["candidate"]["candidate_id"]] = package
        cycle_receipts.append({"cycle": cycle, "checked_count": len(packages), "passed_count": len(packages) - len(failures), "failed_count": len(failures), "failures": failures})
        if not failures:
            break
        # Only deterministic normalization is safe inside this local loop. If
        # no record changed, further cycles would waste work; retain the exact
        # failure receipt for a bounded targeted agent repair.
        if len(cycle_receipts) >= 2 and cycle_receipts[-1]["failures"] == cycle_receipts[-2]["failures"]:
            break
        normalized = [_normalize_record(record) for record in normalized]

    package_root.mkdir(parents=True, exist_ok=True)
    for candidate_id, package in packages.items():
        (package_root / f"{candidate_id}.json").write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")

    # Repair inputs are the authoritative bounded final set. Carrying the
    # prior manifest forward would retain candidates that were deliberately
    # replaced during an editorial cycle and inflate the final count.
    entry_index: Dict[str, Dict[str, Any]] = {}
    for candidate_id, package in packages.items():
        candidate = package["candidate"]
        entry_index[candidate_id] = {
            "package_id": package["package_id"], "candidate_id": candidate_id,
            "account": candidate["account"], "category": candidate["category"],
            "status": package["status"],
            "missing_requirements": package.get("missing_requirements", []),
            "package_path": f"artifacts/cardnews_production_packages/{candidate_id}.json",
        }
    entries = list(entry_index.values())
    ready = sum(item.get("status") == "production_package_ready" for item in entries)
    pending = sum(item.get("status") == "production_package_pending_approval" for item in entries)
    blocked = sum(item.get("status") == "blocked" for item in entries)
    manifest = {
        "schema_version": "cardnews_production_package_index_v1",
        "generated_at": datetime.now().astimezone().isoformat(),
        "status": "ready" if entries and ready == len(entries) else ("partial" if ready else ("pending" if pending else "blocked")),
        "package_count": len(entries), "ready_count": ready, "pending_count": pending, "blocked_count": blocked,
        "packages": entries, "approval_scope": "production_package",
        "render_executed": False, "publish_executed": False, "link_issuance_executed": False,
        "quality_loop": {
            "schema_version": SCHEMA_VERSION,
            "max_cycles": max_cycles,
            "cycles_executed": len(cycle_receipts),
            "editorial_cycles_executed": editorial_cycles,
            "receipts": cycle_receipts,
        },
    }
    (package_root / "latest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (package_root / "quality_loop_receipt.json").write_text(json.dumps(manifest["quality_loop"], ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repair-root", type=Path, default=DEFAULT_REPAIR_ROOT)
    parser.add_argument("--package-root", type=Path, default=DEFAULT_PACKAGE_ROOT)
    parser.add_argument("--max-cycles", type=int, default=10)
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    args = parser.parse_args()
    result = run_quality_loop(args.repair_root, args.package_root, args.max_cycles, args.review_root)
    print(json.dumps({"status": result["status"], "ready_count": result["ready_count"], "pending_count": result["pending_count"], "blocked_count": result["blocked_count"], "quality_loop": result["quality_loop"]}, ensure_ascii=False, indent=2))
    return 0 if result["package_count"] > 0 and result["ready_count"] == result["package_count"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
