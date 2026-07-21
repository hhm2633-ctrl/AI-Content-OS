"""Fail-closed deferred tool assignment for Agent Console jobs.

The policy is data-only: it never loads or executes a tool.  Assignments are
always bounded by both the job policy and the agent profile's allow-list.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "agent_console_tool_assignment_v1"
DEFAULT_RESEARCH_TOOLS = ("filesystem", "project_cli")
KNOWN_ASSIGNABLE_TOOLS = frozenset(
    {"filesystem", "project_cli", "graphify", "hyperframes"}
)
FORBIDDEN_TOOLS = frozenset({"browser", "naeo_blog", "publish", "publishing"})

_CODE_PATTERN = re.compile(
    r"\b(code|coding|architecture|module|refactor|debug|test)\b|"
    r"코드|아키텍처|모듈|리팩터|디버그|테스트",
    re.IGNORECASE,
)
_MOTION_PATTERN = re.compile(
    r"\b(motion|animation|video composition)[ _-]?(plan|planning|storyboard)\b|"
    r"\b(render[ _-]?(plan|planning)|hyperframes[ _-]?(diagnostic|plan|planning))\b|"
    r"(모션|애니메이션|영상\s*구성|렌더)\s*(계획|플래닝|스토리보드|진단)",
    re.IGNORECASE,
)
_PUBLISH_PATTERN = re.compile(
    r"\b(publish|posting|upload|schedule post)\b|게시|발행|업로드|예약\s*게시",
    re.IGNORECASE,
)


def _ordered_unique(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = str(value or "").strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _job_text(job: Mapping[str, Any], context: Mapping[str, Any]) -> str:
    fields = (
        job.get("title"),
        job.get("task_type"),
        context.get("task_type"),
        context.get("objective"),
        context.get("work_type"),
    )
    return " ".join(str(value) for value in fields if value is not None)


def _policy_tools(job: Mapping[str, Any], context: Mapping[str, Any]) -> tuple[list[str], str]:
    text = _job_text(job, context)
    if _PUBLISH_PATTERN.search(text):
        return [], "blocked_publish_intent"
    if _MOTION_PATTERN.search(text):
        return [*DEFAULT_RESEARCH_TOOLS, "hyperframes"], "motion_render_planning"
    if _CODE_PATTERN.search(text):
        return [*DEFAULT_RESEARCH_TOOLS, "graphify"], "code_architecture"
    if str(job.get("category") or "").strip().lower() in {
        "news",
        "story",
        "fashion",
        "beauty",
    }:
        return list(DEFAULT_RESEARCH_TOOLS), "category_read_only_research"
    return [], "unsupported_job"


def assign_deferred_tools(
    job: Mapping[str, Any],
    *,
    allowed_tools: Iterable[str],
    requested_tools: Iterable[str] | None = None,
    context: Mapping[str, Any] | None = None,
    registered_tools: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Return an auditable assignment without loading any deferred adapter.

    Empty ``requested_tools`` means "use safe policy defaults".  Explicit
    requests narrow those defaults; they never broaden them.
    """

    if not isinstance(job, Mapping):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "denied",
            "reason_code": "invalid_job",
            "assigned_tools": [],
            "denied": [{"tool_id": None, "reason_code": "job_must_be_object"}],
        }

    clean_context = context if isinstance(context, Mapping) else {}
    registered = set(_ordered_unique(registered_tools or KNOWN_ASSIGNABLE_TOOLS))
    allowed = _ordered_unique(allowed_tools)
    raw_requested = job.get("requested_tools", ()) if requested_tools is None else requested_tools
    requested = _ordered_unique(raw_requested or ())
    policy_tools, policy_reason = _policy_tools(job, clean_context)
    policy_set = set(policy_tools)
    denied: list[dict[str, Any]] = []

    for tool_id in _ordered_unique([*allowed, *requested]):
        if tool_id in FORBIDDEN_TOOLS:
            denied.append({"tool_id": tool_id, "reason_code": "tool_forbidden"})
        elif tool_id not in registered or tool_id not in KNOWN_ASSIGNABLE_TOOLS:
            denied.append({"tool_id": tool_id, "reason_code": "unknown_tool"})

    desired = requested if requested else policy_tools
    allowed_set = set(allowed)
    assigned: list[str] = []
    for tool_id in desired:
        if tool_id in FORBIDDEN_TOOLS or tool_id not in registered or tool_id not in KNOWN_ASSIGNABLE_TOOLS:
            continue
        if tool_id not in policy_set:
            denied.append({"tool_id": tool_id, "reason_code": "job_policy_denied"})
            continue
        if tool_id not in allowed_set:
            denied.append({"tool_id": tool_id, "reason_code": "agent_not_allowed"})
            continue
        assigned.append(tool_id)

    assigned = _ordered_unique(assigned)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "assigned" if assigned else "denied",
        "reason_code": policy_reason,
        "assignment_mode": "requested_intersection" if requested else "policy_default_intersection",
        "assigned_tools": assigned,
        "policy_tools": policy_tools,
        "allowed_tools": allowed,
        "requested_tools": requested,
        "denied": denied,
        "execution_started": False,
    }


__all__ = [
    "DEFAULT_RESEARCH_TOOLS",
    "FORBIDDEN_TOOLS",
    "KNOWN_ASSIGNABLE_TOOLS",
    "SCHEMA_VERSION",
    "assign_deferred_tools",
]
