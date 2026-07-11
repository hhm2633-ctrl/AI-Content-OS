import json
from pathlib import Path
from typing import Any, Dict, List, Optional


CARD_ROLES = ("hook", "problem", "solution", "cta")


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
            if isinstance(index, int) and 1 <= index <= 4 and index not in cards_by_index:
                cards_by_index[index] = item

    cards = []
    for index, role in enumerate(CARD_ROLES, start=1):
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

    result_complete = result.get("status") == "card_news_completed"
    qa_passed = quality.get("passed") is True
    four_cards_available = len(cards_by_index) == 4 and all(card["exists"] for card in cards)
    publishing_status_ready = publishing.get("status") == "publishing_ready"
    manual_image_required = publishing.get("manual_image_required") is True

    return {
        "schema_version": 1,
        "status": (
            "ready"
            if result_complete
            and qa_passed
            and four_cards_available
            and publishing_status_ready
            and not manual_image_required
            else "incomplete"
        ),
        "title": str(result.get("title", "")),
        "cards": cards,
        "qa": {
            "passed": qa_passed,
            "score": quality.get("qa_score") if isinstance(quality.get("qa_score"), (int, float)) else None,
            "warnings": warnings,
        },
        "publishing": {
            "ready": publishing_status_ready and four_cards_available and not manual_image_required,
            "status": str(publishing.get("status", "unavailable")),
            "platform": str(publishing.get("platform", "")),
            "upload_mode": str(publishing.get("upload_mode", "")),
            "manual_image_required": manual_image_required,
            "next_action": str(publishing.get("next_action", "")),
        },
        "source_files": {
            "card_news_result": _repository_relative(result_path, root),
            "quality": _repository_relative(qa_path, root),
            "publishing": _repository_relative(publishing_path, root),
        },
    }
