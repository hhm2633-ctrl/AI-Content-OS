import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.design_learning.layout_candidate_map import known_layout_ids

CANDIDATE_STATUS = "candidate"
ACCEPTED_POST_TYPE = "carousel_cardnews"

_EVIDENCE_FIELDS = (
    "observed_order",
    "source_surface",
    "account_handle",
    "post_url",
    "visible_post_age",
    "cover_hook_text",
    "cover_visual_type",
    "color_palette",
    "typography_style",
    "image_usage",
    "slide_count_if_visible",
    "cta_type",
    "why_it_stopped_scroll",
    "risk_flags",
    "notes",
)

_OBSERVED_METRIC_FIELDS = ("visible_likes", "visible_comments")

_CONFIDENCE_SENSITIVE_FIELDS = ("cover_hook_text", "cover_visual_type", "why_it_stopped_scroll")


def _load_scan(scan_path: Path, warnings: List[str]) -> Dict[str, Any]:
    try:
        data = json.loads(Path(scan_path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("scan JSON root must be an object")
        return data
    except FileNotFoundError:
        warnings.append(f"scan file is missing: {scan_path}")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        warnings.append(f"scan file could not be read: {scan_path} ({type(exc).__name__})")
    return {}


def _confidence_for(candidate: Dict[str, Any]) -> str:
    risk_flags = candidate.get("risk_flags")
    if isinstance(risk_flags, list) and risk_flags:
        return "low"
    if any(candidate.get(field) is None for field in _CONFIDENCE_SENSITIVE_FIELDS):
        return "low"
    return "medium"


def _build_evidence(candidate: Dict[str, Any]) -> Dict[str, Any]:
    evidence = {field: candidate.get(field) for field in _EVIDENCE_FIELDS}
    evidence["observed_metrics"] = {
        field: candidate.get(field) for field in _OBSERVED_METRIC_FIELDS
    }
    return evidence


def _reject_reason(candidate: Dict[str, Any], layout_ids: tuple) -> Optional[str]:
    if candidate.get("post_type") != ACCEPTED_POST_TYPE:
        return "not_carousel_cardnews"

    layout_id = candidate.get("mapped_existing_layout_candidate")
    if not layout_id:
        return "missing_layout_mapping"
    if layout_id not in layout_ids:
        return "unmapped_layout_id"
    return None


def import_scan(
    scan_path: Path,
    output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Import a design-learning feed scan as CANDIDATE-only layout observations.

    Every accepted record is mapped exclusively to one of the existing
    CardNews layout IDs (see layout_candidate_map.known_layout_ids) and keeps
    status="candidate" -- this never promotes a pattern, never fabricates
    engagement claims beyond what the scan observed, and never touches
    WorkflowEngine, card_news, or publishing.
    """
    warnings: List[str] = []
    scan = _load_scan(Path(scan_path), warnings)
    layout_ids = known_layout_ids()

    raw_candidates = scan.get("candidates", [])
    if not isinstance(raw_candidates, list):
        warnings.append("scan 'candidates' field is missing or malformed")
        raw_candidates = []

    imported: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    for entry in raw_candidates:
        if not isinstance(entry, dict):
            rejected.append({"entry": entry, "reason": "malformed_entry"})
            continue

        reason = _reject_reason(entry, layout_ids)
        if reason is not None:
            rejected.append({
                "observed_order": entry.get("observed_order"),
                "account_handle": entry.get("account_handle"),
                "reason": reason,
            })
            continue

        imported.append({
            "status": CANDIDATE_STATUS,
            "layout_id": entry.get("mapped_existing_layout_candidate"),
            "topic_category_guess": entry.get("topic_category_guess"),
            "confidence": _confidence_for(entry),
            "evidence": _build_evidence(entry),
        })

    result = {
        "schema_version": 1,
        "status": CANDIDATE_STATUS,
        "scan_id": scan.get("scan_id"),
        "scan_date": scan.get("scan_date"),
        "known_layout_ids": list(layout_ids),
        "imported_count": len(imported),
        "rejected_count": len(rejected),
        "candidates": imported,
        "rejected": rejected,
        "warnings": warnings,
    }

    if output_path is not None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return result
