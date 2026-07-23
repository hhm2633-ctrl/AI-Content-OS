"""Approval-gated bridge from a learned blueprint to a renderable package."""

from __future__ import annotations

import copy
from typing import Any, Dict, Mapping


SCHEMA_VERSION = "selected_candidate_production_package_v1"


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _approval(receipt: Any, candidate_id: str) -> Dict[str, Any]:
    if not isinstance(receipt, Mapping):
        return {
            "status": "pending",
            "approved": False,
            "scope": "production_package",
            "reason_code": "package_approval_required",
        }
    approved = (
        _text(receipt.get("status")).lower() == "approved"
        and _text(receipt.get("candidate_id")) == candidate_id
        and _text(receipt.get("scope")) == "production_package"
        and bool(_text(receipt.get("approved_by")))
        and bool(_text(receipt.get("receipt_id")))
    )
    if not approved:
        return {
            "status": "blocked",
            "approved": False,
            "scope": "production_package",
            "reason_code": "invalid_package_approval_receipt",
        }
    return {
        "status": "approved",
        "approved": True,
        "scope": "production_package",
        "approved_by": _text(receipt.get("approved_by")),
        "receipt_id": _text(receipt.get("receipt_id")),
    }


def build_learning_driven_production_package(
    blueprint: Any,
    approval_receipt: Any = None,
) -> Dict[str, Any]:
    if not isinstance(blueprint, Mapping) or blueprint.get("status") != "ready":
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "blocked",
            "reason_code": "learning_blueprint_not_ready",
        }
    candidate_id = _text(blueprint.get("candidate_id"))
    slides = blueprint.get("slides")
    sources = [
        _text(value) for value in blueprint.get("source_refs", []) if _text(value)
    ]
    if (
        not candidate_id
        or not isinstance(slides, list)
        or not slides
        or len(slides) != blueprint.get("slide_count")
        or not sources
        or not _text(blueprint.get("feed_caption"))
    ):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "blocked",
            "reason_code": "blueprint_content_or_sources_incomplete",
            "candidate": {"candidate_id": candidate_id},
        }
    gate = _approval(approval_receipt, candidate_id)
    ready = gate.get("approved") is True
    packaged_slides = copy.deepcopy(slides)
    source_media = [
        copy.deepcopy(dict(value))
        for value in blueprint.get("source_media_candidates", [])
        if isinstance(value, Mapping)
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": (
            "production_package_ready"
            if ready
            else "production_package_pending_approval"
        ),
        "reason_code": (
            "learning_driven_package_composed"
            if ready
            else _text(gate.get("reason_code")) or "package_approval_required"
        ),
        "candidate": {
            "candidate_id": candidate_id,
            "account": _text(blueprint.get("account")),
            "category": _text(blueprint.get("category")),
            "title": _text(blueprint.get("title")),
        },
        "slide_count": len(packaged_slides),
        "story": {
            "summary": _text(packaged_slides[0].get("body")),
            "learning_trace": copy.deepcopy(blueprint.get("learning_trace", {})),
        },
        "evidence": {
            "status": "ready",
            "source_status": "recorded",
            "sources": [{"url": value} for value in sources],
            "assets": source_media,
            "rights_status": (
                "source_editorial_candidates_present"
                if source_media
                else "source_only_editorial"
            ),
        },
        "design_system": copy.deepcopy(blueprint.get("design_system", {})),
        "slides": packaged_slides,
        "feed_caption": _text(blueprint.get("feed_caption")),
        "media_plan": [
            {
                "page": slide.get("page"),
                "slide_role": slide.get("role"),
                "media_type": "editorial",
                "visual_spec": copy.deepcopy(slide.get("visual_spec", {})),
                "source_media_candidate": copy.deepcopy(
                    slide.get("visual_spec", {}).get("source_media_candidate", {})
                ),
                "source_credit": copy.deepcopy(sources),
            }
            for slide in packaged_slides
        ],
        "gates": {
            "package_approval": gate,
            "render": {
                "status": "ready" if ready else "blocked",
                "authorized": False,
                "reason_code": (
                    "execution_requires_explicit_runner"
                    if ready
                    else "package_approval_required"
                ),
            },
            "publish": {
                "status": "blocked",
                "authorized": False,
                "reason_code": "separate_publish_approval_required",
            },
        },
        "receipts": {
            "package_only": True,
            "render_executed": False,
            "publish_executed": False,
            "link_issuance_executed": False,
        },
    }


__all__ = ["SCHEMA_VERSION", "build_learning_driven_production_package"]
