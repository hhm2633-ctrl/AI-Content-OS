import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.card_news.canvas_contract import (
    MAX_ALLOWED_CARD_SLIDE_COUNT,
    allowed_card_canvas_sizes_label,
    is_allowed_card_canvas_size,
    is_allowed_card_slide_count,
)


CARD_ROLES = ("hook", "problem", "solution", "cta")


def _role_for_card_index(index: int) -> str:
    return CARD_ROLES[index - 1] if 1 <= index <= len(CARD_ROLES) else f"slide_{index}"


def _load_json(path: Path, warnings: List[str], label: str) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON root must be an object")
        return data
    except FileNotFoundError:
        warnings.append(f"{label} file is missing: {path.name}")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        warnings.append(f"{label} file could not be read: {path.name} ({type(exc).__name__})")
    return {}


def _repository_relative(path_value: Any, repository_root: Path) -> Optional[str]:
    if not isinstance(path_value, str) or not path_value.strip():
        return None

    candidate = Path(path_value.strip())
    if not candidate.is_absolute():
        candidate = repository_root / candidate

    try:
        relative = candidate.resolve(strict=False).relative_to(repository_root)
    except (OSError, ValueError):
        return None
    return relative.as_posix()


def _optional_bool(value: Any) -> Optional[bool]:
    return value if isinstance(value, bool) else None


def _string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]


def _non_negative_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _output_set_id(value: Any) -> Optional[str]:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _issue(code: str, message: str, card_index: Optional[int] = None) -> Dict[str, Any]:
    issue: Dict[str, Any] = {"code": code, "message": message}
    if card_index is not None:
        issue["card_index"] = card_index
    return issue


def _inspect_card_artifact(
    card: Dict[str, Any], repository_root: Path
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    index = card["index"]
    path = card["path"]
    artifact = {
        "index": index,
        "path": path,
        "exists": False,
        "nonzero": False,
        "decodable": False,
        "width": None,
        "height": None,
        "dimensions_ok": False,
        "valid": False,
    }
    issues: List[Dict[str, Any]] = []

    if path is None:
        issues.append(_issue(
            "CN_ATOMIC_CARD_PATH_INVALID",
            "Card path is missing, invalid, or outside the repository.",
            index,
        ))
        return artifact, issues

    absolute_path = repository_root / path
    artifact["exists"] = absolute_path.is_file()
    if not artifact["exists"]:
        issues.append(_issue(
            "CN_ATOMIC_CARD_FILE_MISSING", "Card PNG file is missing.", index
        ))
        return artifact, issues

    try:
        artifact["nonzero"] = absolute_path.stat().st_size > 0
    except OSError:
        artifact["nonzero"] = False
    if not artifact["nonzero"]:
        issues.append(_issue(
            "CN_ATOMIC_CARD_FILE_EMPTY", "Card PNG file is empty or unreadable.", index
        ))
        return artifact, issues

    try:
        from PIL import Image, UnidentifiedImageError

        with Image.open(absolute_path) as image:
            image.verify()
        with Image.open(absolute_path) as image:
            artifact["width"], artifact["height"] = image.size
            artifact["decodable"] = image.format == "PNG"
    except (ImportError, OSError, UnidentifiedImageError, ValueError):
        artifact["decodable"] = False

    if not artifact["decodable"]:
        issues.append(_issue(
            "CN_ATOMIC_CARD_IMAGE_DECODE_FAILED",
            "Card file is not a decodable PNG.",
            index,
        ))
        return artifact, issues

    artifact["dimensions_ok"] = is_allowed_card_canvas_size(
        (artifact["width"], artifact["height"])
    )
    if not artifact["dimensions_ok"]:
        issues.append(_issue(
            "CN_ATOMIC_CARD_DIMENSIONS_INVALID",
            f"Card PNG must use an allowed canvas size: {allowed_card_canvas_sizes_label()}.",
            index,
        ))
        return artifact, issues

    artifact["valid"] = True
    return artifact, issues


def build_card_news_result_manifest(
    repository_root: Path = Path("."),
    card_news_result_path: Optional[Path] = None,
    quality_path: Optional[Path] = None,
    publishing_result_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Build a read-only, UI-friendly summary of the latest CardNews outputs."""
    root = Path(repository_root).resolve()
    result_path = card_news_result_path or root / "storage/workflow_results/08_card_news_result.json"
    qa_path = quality_path or root / "storage/card_news/card_news_quality.json"
    publishing_path = publishing_result_path or root / "storage/workflow_results/09_publishing_result.json"

    load_warnings: List[str] = []
    result = _load_json(Path(result_path), load_warnings, "card news result")
    quality = _load_json(Path(qa_path), load_warnings, "quality")
    publishing = _load_json(Path(publishing_path), load_warnings, "publishing")

    cards_by_index: Dict[int, Dict[str, Any]] = {}
    raw_cards = result.get("cards", [])
    if isinstance(raw_cards, list):
        for position, item in enumerate(raw_cards, start=1):
            if not isinstance(item, dict):
                continue
            index = item.get("index", position)
            if (
                isinstance(index, int)
                and not isinstance(index, bool)
                and 1 <= index <= MAX_ALLOWED_CARD_SLIDE_COUNT
            ):
                cards_by_index[index] = item

    cards = []
    for index in sorted(cards_by_index):
        role = _role_for_card_index(index)
        source = cards_by_index.get(index, {})
        path = _repository_relative(source.get("card_path"), root)
        exists = bool(path and (root / path).is_file())
        cards.append({
            "index": index,
            "role": role,
            "path": path,
            "exists": exists,
            "headline": str(source.get("headline", "")) if source else "",
            "status": str(source.get("status", "missing")) if source else "missing",
        })
        if source and path is None:
            load_warnings.append(f"card {index} path is invalid or outside the repository")

    qa_warnings = quality.get("warnings", [])
    if not isinstance(qa_warnings, list):
        qa_warnings = ["quality warnings field is malformed"]
    warnings = load_warnings + [str(item) for item in qa_warnings if item]

    quality_checks = quality.get("checks")
    if not isinstance(quality_checks, dict):
        quality_checks = {}
    layout_result = result.get("layout_result")
    if not isinstance(layout_result, dict):
        layout_result = {}
    rendering_result = result.get("rendering_result")
    if not isinstance(rendering_result, dict):
        rendering_result = {}
    image_sourcing_status = result.get("image_sourcing_status")
    if not isinstance(image_sourcing_status, dict):
        image_sourcing_status = {}
    publishing_operations = publishing.get("operations")
    if not isinstance(publishing_operations, dict):
        publishing_operations = {}

    layout_fallback_used = (
        quality_checks.get("layout_fallback_used") is True
        if "layout_fallback_used" in quality_checks
        else layout_result.get("fallback_used") is True
    )
    rendering_fallback_used = (
        quality_checks.get("rendering_fallback_used") is True
        if "rendering_fallback_used" in quality_checks
        else rendering_result.get("fallback_used") is True
    )
    fallback_used = layout_fallback_used or rendering_fallback_used

    result_complete = result.get("status") == "card_news_completed"
    qa_passed = quality.get("passed") is True
    all_cards_available = (
        is_allowed_card_slide_count(len(cards_by_index))
        and len(cards_by_index) == len(cards)
        and all(card["exists"] for card in cards)
    )
    publishing_status_ready = publishing.get("status") == "publishing_ready"
    manual_image_required = (
        publishing.get("manual_image_required") is True
        or image_sourcing_status.get("manual_image_required") is True
    )

    publishing_card_paths = publishing.get("card_paths")
    normalized_publishing_paths = (
        [_repository_relative(path, root) for path in publishing_card_paths]
        if isinstance(publishing_card_paths, list)
        else []
    )
    card_paths_match = (
        len(normalized_publishing_paths) == len(cards)
        and all(path is not None for path in normalized_publishing_paths)
        and normalized_publishing_paths == [card["path"] for card in cards]
    )

    release_issues: List[Dict[str, Any]] = []
    card_paths = [card["path"] for card in cards]
    raw_card_indexes = [
        int(item.get("index", position))
        for position, item in enumerate(raw_cards, start=1)
        if isinstance(item, dict)
        and isinstance(item.get("index", position), int)
        and not isinstance(item.get("index", position), bool)
        and 1 <= item.get("index", position) <= MAX_ALLOWED_CARD_SLIDE_COUNT
    ] if isinstance(raw_cards, list) else []
    raw_card_set_valid = (
        isinstance(raw_cards, list)
        and all(isinstance(item, dict) for item in raw_cards)
        and is_allowed_card_slide_count(len(raw_card_indexes))
        and sorted(raw_card_indexes) == list(range(1, len(raw_card_indexes) + 1))
    )
    if not raw_card_set_valid:
        release_issues.append(_issue(
            "CN_ATOMIC_CARD_COUNT_INVALID",
            "CardNews records must be contiguous from index 1 with an allowed slide count.",
        ))
    if any(path is None for path in card_paths):
        release_issues.append(_issue(
            "CN_ATOMIC_CARD_PATH_INVALID",
            "All CardNews paths must be repository-relative paths.",
        ))
    valid_card_paths = [path for path in card_paths if path is not None]
    if len(set(valid_card_paths)) != len(valid_card_paths):
        release_issues.append(_issue(
            "CN_ATOMIC_CARD_PATH_DUPLICATE", "CardNews paths must be unique."
        ))
    valid_publishing_paths = [path for path in normalized_publishing_paths if path is not None]
    if len(valid_publishing_paths) != len(set(valid_publishing_paths)):
        release_issues.append(_issue(
            "CN_ATOMIC_PUBLISHING_PATH_DUPLICATE",
            "Publishing card paths must be unique.",
        ))
    if not card_paths_match:
        release_issues.append(_issue(
            "CN_ATOMIC_CARD_PATHS_MISMATCH",
            "Publishing card paths must exactly match the ordered CardNews paths.",
        ))

    card_artifacts = []
    for card in cards:
        artifact, artifact_issues = _inspect_card_artifact(card, root)
        card_artifacts.append(artifact)
        release_issues.extend(artifact_issues)

    output_set_ids = {
        "card_news_result": _output_set_id(result.get("output_set_id")),
        "quality": _output_set_id(quality.get("output_set_id")),
        "publishing": _output_set_id(publishing.get("output_set_id")),
    }
    present_output_set_ids = [value for value in output_set_ids.values() if value is not None]
    if not present_output_set_ids:
        output_set_status = "missing"
        release_issues.append(_issue(
            "CN_ATOMIC_OUTPUT_SET_ID_MISSING",
            "A common output_set_id is required across CardNews, quality, and publishing results.",
        ))
    elif len(present_output_set_ids) != len(output_set_ids):
        output_set_status = "incomplete"
        release_issues.append(_issue(
            "CN_ATOMIC_OUTPUT_SET_ID_INCOMPLETE",
            "output_set_id is present in only some required result files.",
        ))
    elif len(set(present_output_set_ids)) != 1:
        output_set_status = "mismatch"
        release_issues.append(_issue(
            "CN_ATOMIC_OUTPUT_SET_ID_MISMATCH",
            "output_set_id must be identical across all required result files.",
        ))
    else:
        output_set_status = "consistent"
    output_set_consistent = output_set_status == "consistent"

    unlicensed_asset_not_rendered = _optional_bool(
        quality_checks.get("unlicensed_asset_not_rendered")
    )
    attribution_needed = _optional_bool(quality_checks.get("attribution_needed"))
    attribution_present = _optional_bool(quality_checks.get("attribution_present"))
    rights_ready = (
        unlicensed_asset_not_rendered is True
        and (
            attribution_needed is False
            or (attribution_needed is True and attribution_present is True)
        )
    )
    rights_status = "pass" if rights_ready else (
        "unknown"
        if unlicensed_asset_not_rendered is None or attribution_needed is None
        else "blocked"
    )
    if rights_status == "unknown":
        release_issues.append(_issue(
            "CARD_NEWS_RIGHTS_UNKNOWN",
            "CardNews rights checks are incomplete or unavailable.",
        ))
    elif rights_status == "blocked":
        release_issues.append(_issue(
            "CARD_NEWS_RIGHTS_BLOCKED",
            "CardNews rights or attribution checks did not pass.",
        ))

    release_guard_ready = not release_issues and output_set_consistent

    blocking_reasons = _string_list(publishing_operations.get("blocking_reasons"))
    publishing_blocked = (
        publishing_operations.get("publishing_blocked") is True
        or bool(blocking_reasons)
        or publishing.get("status") == "publishing_blocked"
        or manual_image_required
        or not card_paths_match
        or not release_guard_ready
    )
    if not card_paths_match and "card_paths_mismatch" not in blocking_reasons:
        blocking_reasons.append("card_paths_mismatch")
    for release_issue in release_issues:
        if release_issue["code"] not in blocking_reasons:
            blocking_reasons.append(release_issue["code"])

    evidence_available = _optional_bool(quality_checks.get("evidence_available"))
    evidence_applied = _optional_bool(quality_checks.get("evidence_applied"))
    social_proof_available = _optional_bool(quality_checks.get("social_proof_available"))
    social_proof_applied = _optional_bool(quality_checks.get("social_proof_applied"))
    evidence_status = (
        "applied"
        if evidence_applied is True
        else "unavailable"
        if evidence_available is False
        else "not_applied"
        if evidence_available is True and evidence_applied is False
        else "unknown"
    )

    publishing_ready = (
        publishing_status_ready
        and all_cards_available
        and card_paths_match
        and release_guard_ready
        and rights_ready
        and not publishing_blocked
        and not manual_image_required
    )

    return {
        "schema_version": 1,
        "status": (
            "ready"
            if result_complete
            and qa_passed
            and all_cards_available
            and publishing_ready
            else "incomplete"
        ),
        "title": str(result.get("title", "")),
        "cards": cards,
        "qa": {
            "passed": qa_passed,
            "score": quality.get("qa_score") if isinstance(quality.get("qa_score"), (int, float)) else None,
            "warnings": warnings,
            "layout_fallback_used": layout_fallback_used,
            "rendering_fallback_used": rendering_fallback_used,
            "fallback_used": fallback_used,
        },
        "publishing": {
            "ready": publishing_ready,
            "status": str(publishing.get("status", "unavailable")),
            "platform": str(publishing.get("platform", "")),
            "upload_mode": str(publishing.get("upload_mode", "")),
            "manual_image_required": manual_image_required,
            "next_action": str(publishing.get("next_action", "")),
            "blocked": publishing_blocked,
            "blocking_reasons": blocking_reasons,
            "required_action": str(publishing_operations.get("required_action", "")),
            "real_image_used_count": _non_negative_int(
                publishing_operations.get("real_image_used_count")
            ),
            "card_paths_match": card_paths_match,
        },
        "image_sourcing": {
            "manual_image_required": manual_image_required,
            "checklist": _string_list(image_sourcing_status.get("checklist")),
            "recommended_source": str(image_sourcing_status.get("recommended_source", "")),
            "reason": str(image_sourcing_status.get("reason", "")),
        },
        "rights": {
            "status": rights_status,
            "ready": rights_ready,
            "unlicensed_asset_not_rendered": unlicensed_asset_not_rendered,
            "attribution_needed": attribution_needed,
            "attribution_present": attribution_present,
        },
        "evidence": {
            "status": evidence_status,
            "available": evidence_available,
            "applied": evidence_applied,
            "social_proof_available": social_proof_available,
            "social_proof_applied": social_proof_applied,
        },
        "output_set_identity": {
            "status": output_set_status,
            "consistent": output_set_consistent,
            "ids": output_set_ids,
        },
        "release_guard": {
            "ready": release_guard_ready,
            "issue_codes": [issue["code"] for issue in release_issues],
            "issues": release_issues,
            "card_artifacts": card_artifacts,
        },
        "source_files": {
            "card_news_result": _repository_relative(result_path, root),
            "quality": _repository_relative(qa_path, root),
            "publishing": _repository_relative(publishing_path, root),
        },
    }
