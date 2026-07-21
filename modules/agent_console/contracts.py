"""Serializable contracts for the local agent console.

The console records orchestration state only. It does not call a paid model API,
publish content, issue affiliate links, or resume an automation.
"""

from __future__ import annotations

import copy
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional


CATEGORIES = ("news", "story", "fashion", "beauty")
BACKENDS = ("codex", "claude_cli", "spark", "local")
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
JOB_STATUSES = {
    "awaiting_second_stage",
    "queued",
    "running",
    "completed",
    "failed",
    "cancelled",
    "blocked",
}
_SENSITIVE_KEY = re.compile(
    r"(^|_)(api_?key|access_?token|refresh_?token|secret|password|cookie|authorization)($|_)",
    re.IGNORECASE,
)


def sanitize_json(value: Any) -> Any:
    """Deep-copy JSON-like data while removing obvious secret-bearing fields."""

    if isinstance(value, Mapping):
        clean: Dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            clean[key] = "[REDACTED]" if _SENSITIVE_KEY.search(key) else sanitize_json(raw_value)
        return clean
    if isinstance(value, (list, tuple)):
        return [sanitize_json(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return copy.deepcopy(value)
    return str(value)


@dataclass(frozen=True)
class AgentLimits:
    max_steps: int = 6
    timeout_seconds: int = 300
    max_retries: int = 1

    def __post_init__(self) -> None:
        if not 1 <= self.max_steps <= 100:
            raise ValueError("max_steps must be between 1 and 100")
        if not 1 <= self.timeout_seconds <= 86_400:
            raise ValueError("timeout_seconds must be between 1 and 86400")
        if not 0 <= self.max_retries <= 10:
            raise ValueError("max_retries must be between 0 and 10")


@dataclass(frozen=True)
class AgentProfile:
    agent_id: str
    category: str
    backend: str
    allowed_tools: tuple[str, ...] = ()
    limits: AgentLimits = field(default_factory=AgentLimits)
    session_key: Optional[str] = None
    model_reasoning_summary: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.agent_id.strip():
            raise ValueError("agent_id is required")
        if self.category not in (*CATEGORIES, "all"):
            raise ValueError(f"unsupported category: {self.category}")
        if self.backend not in BACKENDS:
            raise ValueError(f"unsupported backend: {self.backend}")
        if self.backend == "claude_cli" and not (self.session_key or "").strip():
            raise ValueError("Claude CLI requires one reusable session_key")
        if self.backend == "spark" and self.model_reasoning_summary != "none":
            raise ValueError('Spark requires model_reasoning_summary="none"')

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["allowed_tools"] = list(self.allowed_tools)
        return payload


@dataclass(frozen=True)
class Handoff:
    summary: str
    outputs: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.summary.strip():
            raise ValueError("handoff summary is required")
        if len(self.summary) > 500:
            raise ValueError("handoff summary must be 500 characters or fewer")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary.strip(),
            "outputs": sanitize_json(self.outputs),
            "warnings": [str(item)[:300] for item in self.warnings[:10]],
        }
