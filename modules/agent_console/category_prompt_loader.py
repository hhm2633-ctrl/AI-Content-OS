"""Category-specific execution prompt loader for the Agent Console.

Renders the Agency Agents-derived education asset
(`knowledge/agent_training/category_execution_prompts.json`) into one short
structured block for the dispatched job category. A missing, invalid, or
unknown-category asset degrades to an empty block so dispatch never fails on
education data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ASSET_PATH = (
    REPOSITORY_ROOT / "knowledge" / "agent_training" / "category_execution_prompts.json"
)


def load_category_prompts(asset_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(asset_path) if asset_path is not None else DEFAULT_ASSET_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _lines(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def build_category_prompt(category: str, *, asset_path: str | Path | None = None) -> str:
    payload = load_category_prompts(asset_path)
    categories = payload.get("categories")
    if not isinstance(categories, dict):
        return ""
    normalized = str(category or "").strip().lower()
    entry = categories.get(normalized)
    if not isinstance(entry, dict):
        return ""
    rules = _lines(entry.get("rules"))
    prohibited = _lines(entry.get("prohibited"))
    if not rules and not prohibited:
        return ""
    parts = [f"[카테고리 실행 교육 | {normalized} | {entry.get('label', '')}]"]
    if rules:
        parts.append("규칙: " + " / ".join(rules))
    if prohibited:
        parts.append("금지: " + " / ".join(prohibited))
    shared = payload.get("shared") if isinstance(payload.get("shared"), dict) else {}
    shared_rules = _lines(shared.get("rules"))
    if shared_rules:
        parts.append("공통: " + " / ".join(shared_rules))
    shared_prohibited = _lines(shared.get("prohibited"))
    if shared_prohibited:
        parts.append("공통 금지: " + " / ".join(shared_prohibited))
    precedence = str(payload.get("precedence") or "").strip()
    if precedence:
        parts.append(f"우선순위: {precedence}")
    return " ".join(parts)


__all__ = ["DEFAULT_ASSET_PATH", "build_category_prompt", "load_category_prompts"]
