"""Pure completion gate for Agent Console CardNews package results.

The gate only inspects an already-produced result.  It never runs a command,
reads or writes a file, renders media, publishes content, or issues links.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple


SCHEMA_VERSION = "agent_console_package_completion_gate_v1"
SUPPORTED_ACCOUNTS = {"A", "B", "C"}
PACKAGE_KEYS = (
    "production_package",
    "selected_candidate_production_package",
    "package",
)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _package(value: Any) -> Mapping[str, Any] | None:
    """Unwrap only explicit Agent Console/package result envelopes."""

    if not isinstance(value, Mapping):
        return None
    for key in PACKAGE_KEYS:
        candidate = value.get(key)
        if isinstance(candidate, Mapping):
            return candidate
    outputs = value.get("outputs")
    if isinstance(outputs, Mapping):
        for key in PACKAGE_KEYS:
            candidate = outputs.get(key)
            if isinstance(candidate, Mapping):
                return candidate
    handoff = value.get("handoff")
    if isinstance(handoff, Mapping):
        outputs = handoff.get("outputs")
        if isinstance(outputs, Mapping):
            for key in PACKAGE_KEYS:
                candidate = outputs.get(key)
                if isinstance(candidate, Mapping):
                    return candidate
    return value


def _receipt(field: str, reason_code: str, detail: str) -> Dict[str, str]:
    return {"field": field, "reason_code": reason_code, "detail": detail}


def _objects(value: Any) -> List[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _indexed_pages(rows: List[Mapping[str, Any]]) -> Tuple[Dict[int, Mapping[str, Any]], List[int]]:
    indexed: Dict[int, Mapping[str, Any]] = {}
    invalid: List[int] = []
    for fallback_page, row in enumerate(rows, start=1):
        raw_page = row.get("page", fallback_page)
        try:
            page = int(raw_page)
        except (TypeError, ValueError):
            invalid.append(fallback_page)
            continue
        if page < 1 or page in indexed:
            invalid.append(page)
            continue
        indexed[page] = row
    return indexed, invalid


def assess_package_completion(result: Any) -> Dict[str, Any]:
    """Return a fail-closed, side-effect-free package completion receipt."""

    package = _package(result)
    missing: List[Dict[str, str]] = []
    candidate_id = ""
    account = ""

    if not isinstance(package, Mapping):
        missing.append(
            _receipt("package", "package_result_missing", "an object-shaped package result is required")
        )
    else:
        candidate = package.get("candidate")
        candidate = candidate if isinstance(candidate, Mapping) else {}
        candidate_id = _text(candidate.get("candidate_id")) or _text(package.get("candidate_id"))
        account = (_text(candidate.get("account")) or _text(package.get("account"))).upper()
        if not candidate_id:
            missing.append(
                _receipt("candidate.candidate_id", "candidate_id_missing", "candidate identity is required")
            )
        if account not in SUPPORTED_ACCOUNTS:
            missing.append(
                _receipt("candidate.account", "account_missing_or_unsupported", "account must be A, B, or C")
            )

        story = package.get("story")
        story = story if isinstance(story, Mapping) else {}
        story_text = _text(story.get("summary")) or _text(story.get("narrative"))
        if not story_text:
            missing.append(
                _receipt("story", "source_backed_story_missing", "story summary or narrative is required")
            )

        evidence = package.get("evidence")
        evidence = evidence if isinstance(evidence, Mapping) else {}
        sources = evidence.get("sources")
        source_rows = []
        if isinstance(sources, list):
            source_rows = [
                item
                for item in sources
                if _text(item)
                or (
                    isinstance(item, Mapping)
                    and (_text(item.get("url")) or _text(item.get("source_url")))
                )
            ]
        if not source_rows:
            missing.append(
                _receipt("evidence.sources", "story_sources_missing", "at least one recorded source is required")
            )

        slides_value = package.get("slides")
        if not isinstance(slides_value, list):
            slides_value = package.get("slide_copy")
        slides = _objects(slides_value)
        slides_by_page, invalid_slide_pages = _indexed_pages(slides)
        if not slides:
            missing.append(
                _receipt("slides", "slide_copy_missing", "at least one completed slide is required")
            )
        if invalid_slide_pages:
            missing.append(
                _receipt("slides.page", "slide_pages_invalid", "slide pages must be unique positive integers")
            )

        declared_count = package.get("slide_count")
        if declared_count is not None:
            try:
                count_matches = int(declared_count) == len(slides_by_page)
            except (TypeError, ValueError):
                count_matches = False
            if not count_matches:
                missing.append(
                    _receipt("slide_count", "slide_count_mismatch", "declared slide count must match completed copy")
                )

        for page in sorted(slides_by_page):
            slide = slides_by_page[page]
            if not _text(slide.get("headline")):
                missing.append(
                    _receipt(f"slides[{page}].headline", "slide_headline_missing", f"slide {page} needs a headline")
                )
            if not _text(slide.get("body")):
                missing.append(
                    _receipt(f"slides[{page}].body", "slide_body_missing", f"slide {page} needs body copy")
                )

        if not _text(package.get("feed_caption")):
            missing.append(
                _receipt("feed_caption", "feed_caption_missing", "a separate nonempty feed caption is required")
            )

        media = _objects(package.get("media_plan"))
        media_by_page, invalid_media_pages = _indexed_pages(media)
        if not media:
            missing.append(
                _receipt("media_plan", "media_plan_missing", "one media plan entry per slide is required")
            )
        if invalid_media_pages:
            missing.append(
                _receipt("media_plan.page", "media_pages_invalid", "media pages must be unique positive integers")
            )
        expected_pages = set(slides_by_page)
        if set(media_by_page) != expected_pages:
            missing.append(
                _receipt("media_plan", "media_plan_incomplete", "media plan pages must exactly match slide pages")
            )
        for page in sorted(expected_pages & set(media_by_page)):
            media_item = media_by_page[page]
            if not _text(media_item.get("media_type")):
                missing.append(
                    _receipt(f"media_plan[{page}].media_type", "media_type_missing", f"slide {page} needs a media type")
                )
            if not (_text(media_item.get("slide_role")) or _text(media_item.get("role"))):
                missing.append(
                    _receipt(f"media_plan[{page}].slide_role", "media_role_missing", f"slide {page} needs a media role")
                )

    complete = not missing
    missing_fields = [item["field"] for item in missing]

    def passed(*prefixes: str) -> bool:
        return not any(
            field == prefix or field.startswith(f"{prefix}.") or field.startswith(f"{prefix}[")
            for field in missing_fields
            for prefix in prefixes
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "complete" if complete else "blocked",
        "reason_code": "package_completion_requirements_met" if complete else "package_completion_requirements_missing",
        "package_complete": complete,
        "candidate_id": candidate_id or None,
        "account": account or None,
        "missing_fields": missing_fields,
        "missing_field_receipts": missing,
        "checks": {
            "candidate_account_identity": passed("candidate"),
            "source_backed_story": passed("story", "evidence"),
            "variable_slide_copy": passed("slides", "slide_count"),
            "separate_feed_caption": passed("feed_caption"),
            "per_slide_media_plan": passed("media_plan"),
        },
        "execution": {
            "commands_executed": False,
            "files_written": False,
            "render_executed": False,
            "publish_executed": False,
            "link_issuance_executed": False,
            "external_calls_executed": False,
        },
    }


__all__ = ["assess_package_completion", "SCHEMA_VERSION"]
