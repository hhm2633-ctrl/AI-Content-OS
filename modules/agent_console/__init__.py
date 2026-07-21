"""Local, API-neutral work-order console for bounded category agents."""

from modules.agent_console.console import AgentConsole
from modules.agent_console.contracts import AgentLimits, AgentProfile, Handoff
from modules.agent_console.tool_manifest import LazyToolRegistry, ToolSpec

__all__ = [
    "AgentConsole",
    "AgentLimits",
    "AgentProfile",
    "Handoff",
    "LazyToolRegistry",
    "ToolSpec",
]
