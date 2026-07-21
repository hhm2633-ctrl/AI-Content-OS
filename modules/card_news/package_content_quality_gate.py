"""Account-aware, side-effect-free quality gate for CardNews packages."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from modules.agent_console.package_completion_gate import assess_package_completion


SCHEMA_VERSION = "cardnews_package_content_quality_gate_v1"
FORBIDDEN_PUBLIC_COPY = ("세탁 회전", "카피 소스", "내부 기획", "슬라이드에서")
ALLOWED_ASSET_STATUS = {
    "official_source",
    "source_reference",
    "original_editorial_graphic",
    "verified_real_comment",
    "labeled_reenactment",
    "generated_auxiliary",
    "product_source",
    "planned_not_rendered",
    "ready_for_editorial_production",
    "scene_direction_ready_not_generated",
}

UNRESOLVED_ASSET_STATUS = {
    "official_asset_discovery_required",
    "official_source_asset_discovery_required",
    "source_clip_identified_not_acquired",
    "source_page_observed_not_acquired",
    "official_clip_discovery_required",
    "embedded_clip_identified_not_acquired",
}


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _objects(value: Any) -> List[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _failure(field: str, reason_code: str, detail: str) -> Dict[str, str]:
    return {"field": field, "reason_code": reason_code, "detail": detail}


def assess_package_content_quality(package: Any) -> Dict[str, Any]:
    """Judge reviewability, not Instagram performance or subjective perfection."""

    completion = assess_package_completion(package)
    failures: List[Dict[str, str]] = []
    if not completion["package_complete"]:
        failures.extend(completion["missing_field_receipts"])

    value = package if isinstance(package, Mapping) else {}
    candidate = value.get("candidate")
    candidate = candidate if isinstance(candidate, Mapping) else {}
    account = _text(candidate.get("account")).upper()
    slides = _objects(value.get("slides"))
    media = _objects(value.get("media_plan"))

    if slides and not 3 <= len(slides) <= 10:
        failures.append(_failure("slides", "slide_count_out_of_review_range", "use a topic-led variable 3-10 slide structure"))

    seen_copy: set[tuple[str, str]] = set()
    roles: set[str] = set()
    headline_limit = 30 if account == "C" else 42
    body_limit = 90 if account == "C" else 140
    for position, slide in enumerate(slides, start=1):
        headline = _text(slide.get("headline"))
        body = _text(slide.get("body"))
        role = _text(slide.get("role")) or _text(slide.get("slide_role"))
        roles.add(role)
        if len(headline) > headline_limit:
            failures.append(_failure(f"slides[{position}].headline", "headline_too_dense", f"headline exceeds {headline_limit} characters"))
        if len(body) > body_limit:
            failures.append(_failure(f"slides[{position}].body", "body_too_dense", f"body exceeds {body_limit} characters"))
        public_copy = f"{headline} {body}"
        for phrase in FORBIDDEN_PUBLIC_COPY:
            if phrase in public_copy:
                failures.append(_failure(f"slides[{position}]", "internal_jargon_in_public_copy", phrase))
        pair = (headline, body)
        if pair in seen_copy:
            failures.append(_failure(f"slides[{position}]", "duplicate_slide_copy", "each slide must advance the story"))
        seen_copy.add(pair)

    caption = _text(value.get("feed_caption"))
    if caption and len(caption) < 35:
        failures.append(_failure("feed_caption", "feed_caption_too_thin", "feed caption needs at least two natural sentences"))
    if caption and any(caption == _text(slide.get("body")) for slide in slides):
        failures.append(_failure("feed_caption", "feed_caption_duplicates_slide", "feed caption must add context outside the carousel"))

    for position, item in enumerate(media, start=1):
        credit = item.get("source_credit")
        credits = [entry for entry in credit if _text(entry)] if isinstance(credit, list) else ([_text(credit)] if _text(credit) else [])
        if not credits:
            failures.append(_failure(f"media_plan[{position}].source_credit", "media_source_credit_missing", "record the source used for this media role"))
        status = _text(item.get("asset_status"))
        acquisition_status = _text(item.get("acquisition_status"))
        if acquisition_status in {"not_acquired", "discovery_required"}:
            failures.append(
                _failure(
                    f"media_plan[{position}].acquisition_status",
                    "unresolved_media_dependency",
                    "the package still depends on source media that has not been acquired",
                )
            )
        if status in UNRESOLVED_ASSET_STATUS:
            failures.append(
                _failure(
                    f"media_plan[{position}].asset_status",
                    "unresolved_media_dependency",
                    "replace unacquired source media with an owned editorial plan or acquire it before package approval",
                )
            )
        elif status not in ALLOWED_ASSET_STATUS:
            failures.append(_failure(f"media_plan[{position}].asset_status", "media_asset_status_unapproved", status or "missing"))

    if account == "B" and len({role for role in roles if role}) < 3:
        failures.append(_failure("slides.role", "emotional_progression_not_visible", "account B needs at least three distinct scene roles"))

    if account == "C" and slides:
        first = slides[0]
        if len(_text(first.get("headline"))) > 26 or len(_text(first.get("body"))) > 72:
            failures.append(_failure("slides[1]", "account_c_first_frame_not_concise", "beauty/fashion first frame must be visual-first and concise"))

    unique = []
    seen_reasons = set()
    for item in failures:
        key = (item["field"], item["reason_code"])
        if key not in seen_reasons:
            seen_reasons.add(key)
            unique.append(item)
    passed = not unique
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed" if passed else "repair_required",
        "quality_passed": passed,
        "candidate_id": completion.get("candidate_id"),
        "account": completion.get("account"),
        "completion_receipt": completion,
        "failure_count": len(unique),
        "failures": unique,
        "performance_claimed": False,
        "subjective_perfection_claimed": False,
        "execution": {
            "render": False,
            "publish": False,
            "link_issuance": False,
            "external_calls": False,
        },
    }


__all__ = ["assess_package_content_quality", "SCHEMA_VERSION"]
