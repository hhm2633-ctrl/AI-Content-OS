"""CardNews design-learning adapter.

This module turns existing Instagram/card-news research artifacts into a
small, deterministic design-candidate registry for CardNews production.

Important boundaries:
- It does not scrape Instagram.
- It does not promote anything to "verified" or "proven".
- It does not add an 11th layout.
- It maps observed visual/hook/story patterns onto the existing 10 layout IDs.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


INSTAGRAM_LEARNING_DIR = os.path.join(
    "external_workclaude",
    "instagram_broad_learning_v1",
)
LAYOUT_RULES_PATH = os.path.join("templates", "card_news_layout_rules.json")

ALLOWED_CONFIDENCE = {"benchmark_observed", "hypothesis_only"}
ALLOWED_STATUSES = {"CANDIDATE"}

# Existing layout IDs from templates/card_news_layout_rules.json.  Do not add
# a layout here unless the renderer/layout-rule contract is explicitly changed.
VISUAL_FAMILY_TO_LAYOUT = {
    "인물/실사진 풀프레임 + 하단 좌측 볼드 타이포": "dark_editorial",
    "손글씨/스크랩북 콜라주 스타일": "notebook",
    "다크(블랙) 배경 + 네온/형광 대비 타이포": "bold_ai",
    "일러스트 캐릭터/의인화 아이콘형": "character_diary",
    "미니멀 화이트 배경 + 버튼형 CTA 그래픽": "checklist",
    "앱 UI 목업 재현형": "comparison",
    "데이터 대시보드/카드형": "number_list",
    "텍스트 오버레이 없는 순수 사진형(캡션 의존)": "dark_editorial",
    "흑백 매거진풍 하이엔드 레이아웃": "dark_editorial",
}

HOOK_TO_LAYOUT_HINT = {
    "타임리밋": "timeline",
    "숫자": "number_list",
    "공식": "tutorial",
    "문제 원인": "warning",
    "비교": "comparison",
    "무료자료": "checklist",
    "사건": "dark_editorial",
    "가정형": "checklist",
}

STORY_TO_STRUCTURE_HINT = {
    "문제-공식-행동유도형": ["hook", "problem", "solution", "cta"],
    "번호형 큐레이션 리스트": ["hook", "problem", "solution", "cta"],
    "사건-논란 제기-의견 유도형": ["hook", "problem", "solution", "cta"],
    "데이터 브리핑형": ["hook", "problem", "solution", "cta"],
}


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_layout_ids(path: str = LAYOUT_RULES_PATH) -> List[str]:
    data = _read_json(path)
    return sorted((data.get("layouts") or {}).keys())


def _confidence(value: Any) -> str:
    text = str(value or "").strip()
    return text if text in ALLOWED_CONFIDENCE else "hypothesis_only"


def _candidate_id(prefix: str, name: str) -> str:
    normalized = "".join(
        char.lower() if char.isalnum() else "_"
        for char in name
    )
    normalized = "_".join(part for part in normalized.split("_") if part)
    return f"{prefix}_{normalized[:80]}"


def _safe_urls(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item.startswith("http")]


def _choose_hook_layout(pattern_name: str, layout_ids: List[str]) -> str:
    for marker, layout_id in HOOK_TO_LAYOUT_HINT.items():
        if marker in pattern_name and layout_id in layout_ids:
            return layout_id
    return "bold_ai" if "bold_ai" in layout_ids else layout_ids[0]


def build_design_candidates(
    learning_dir: str = INSTAGRAM_LEARNING_DIR,
    layout_rules_path: str = LAYOUT_RULES_PATH,
) -> Dict[str, Any]:
    layout_ids = load_layout_ids(layout_rules_path)
    visual_data = _read_json(os.path.join(learning_dir, "VISUAL_LAYOUT_LIBRARY.json"))
    hook_data = _read_json(os.path.join(learning_dir, "HOOK_PATTERN_LIBRARY.json"))
    story_data = _read_json(os.path.join(learning_dir, "STORY_STRUCTURE_LIBRARY.json"))

    candidates: List[Dict[str, Any]] = []

    for family in visual_data.get("layout_families", []):
        family_name = str(family.get("family", "")).strip()
        layout_id = VISUAL_FAMILY_TO_LAYOUT.get(family_name, "bold_ai")
        if layout_id not in layout_ids:
            layout_id = "bold_ai" if "bold_ai" in layout_ids else layout_ids[0]

        candidates.append(
            {
                "candidate_id": _candidate_id("visual", family_name),
                "candidate_type": "visual_layout",
                "status": "CANDIDATE",
                "confidence": _confidence(family.get("confidence")),
                "source_claim_ids": _safe_urls(family.get("evidence_urls")),
                "observed_pattern": family_name,
                "recommended_existing_layout": layout_id,
                "recommended_usage": family.get("description", ""),
                "risk_flags": [],
                "allowed_for_autopick": family.get("confidence") == "benchmark_observed",
                "notes": family.get("note", ""),
            }
        )

    for pattern in hook_data.get("patterns", []):
        pattern_name = str(pattern.get("pattern", "")).strip()
        candidates.append(
            {
                "candidate_id": _candidate_id("hook", pattern_name),
                "candidate_type": "cover_hook",
                "status": "CANDIDATE",
                "confidence": _confidence(pattern.get("confidence")),
                "source_claim_ids": _safe_urls(pattern.get("evidence_urls")),
                "observed_pattern": pattern_name,
                "recommended_existing_layout": _choose_hook_layout(pattern_name, layout_ids),
                "recommended_usage": pattern.get("description", ""),
                "risk_flags": ["needs_fact_check"] if "성과" in pattern_name or "권위" in pattern_name else [],
                "allowed_for_autopick": pattern.get("confidence") == "benchmark_observed",
                "notes": pattern.get("note", ""),
            }
        )

    for structure in story_data.get("structures", []):
        structure_name = str(structure.get("structure", "")).strip()
        candidates.append(
            {
                "candidate_id": _candidate_id("story", structure_name),
                "candidate_type": "story_structure",
                "status": "CANDIDATE",
                "confidence": _confidence(structure.get("confidence")),
                "source_claim_ids": _safe_urls(structure.get("evidence_urls")),
                "observed_pattern": structure_name,
                "recommended_existing_layout": _choose_hook_layout(structure_name, layout_ids),
                "recommended_slide_roles": STORY_TO_STRUCTURE_HINT.get(
                    structure_name,
                    ["hook", "problem", "solution", "cta"],
                ),
                "recommended_usage": " / ".join(structure.get("steps", [])),
                "risk_flags": ["comment_cta_review"] if "의견 유도" in structure_name else [],
                "allowed_for_autopick": structure.get("confidence") == "benchmark_observed",
                "notes": structure.get("note", ""),
            }
        )

    return {
        "schema_version": "card_news_design_learning_v1",
        "generated_at": datetime.now().isoformat(),
        "source": learning_dir.replace("\\", "/"),
        "layout_rules_path": layout_rules_path.replace("\\", "/"),
        "existing_layout_ids": layout_ids,
        "candidate_count": len(candidates),
        "promotion_policy": (
            "All imported items are CANDIDATE. Real performance data and human "
            "approval are required before VERIFIED/PROMOTED use."
        ),
        "candidates": candidates,
    }


def validate_design_candidates(payload: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if not isinstance(payload, dict):
        return ["payload_not_dict"]

    layout_ids = set(payload.get("existing_layout_ids") or [])
    seen = set()
    for candidate in payload.get("candidates") or []:
        candidate_id = candidate.get("candidate_id")
        if not candidate_id:
            errors.append("missing_candidate_id")
        elif candidate_id in seen:
            errors.append(f"duplicate_candidate_id:{candidate_id}")
        seen.add(candidate_id)

        if candidate.get("status") not in ALLOWED_STATUSES:
            errors.append(f"invalid_status:{candidate_id}")
        if candidate.get("confidence") not in ALLOWED_CONFIDENCE:
            errors.append(f"invalid_confidence:{candidate_id}")
        if candidate.get("recommended_existing_layout") not in layout_ids:
            errors.append(f"unknown_layout:{candidate_id}")
        if candidate.get("candidate_type") not in {
            "visual_layout",
            "cover_hook",
            "story_structure",
        }:
            errors.append(f"invalid_candidate_type:{candidate_id}")
        if not candidate.get("source_claim_ids"):
            errors.append(f"missing_source_claim_ids:{candidate_id}")

    return errors
