"""Central registry of every offline tool available to agents."""

from __future__ import annotations

from app.agents.tools.base import Tool, ToolContext, ToolError
from app.agents.tools.calculator import calculator_tool
from app.agents.tools.database import database_tool
from app.agents.tools.filesystem import filesystem_tool
from app.agents.tools.network import github_tool, weather_tool
from app.agents.tools.notes import notes_tool
from app.agents.tools.utility import echo_tool, time_tool

# Ordered so the default agent gets a sensible tool list: offline tools first,
# then the two that need the internet (and are disabled by default).
_TOOLS: dict[str, Tool] = {
    calculator_tool.name: calculator_tool,
    notes_tool.name: notes_tool,
    database_tool.name: database_tool,
    filesystem_tool.name: filesystem_tool,
    time_tool.name: time_tool,
    echo_tool.name: echo_tool,
    weather_tool.name: weather_tool,
    github_tool.name: github_tool,
}


def all_tools() -> list[Tool]:
    return list(_TOOLS.values())


def tool_names() -> list[str]:
    return list(_TOOLS.keys())


def offline_tool_names() -> list[str]:
    """Tools that work with no internet access. Used for the seeded demo agent."""
    return [name for name, tool in _TOOLS.items() if not tool.requires_network]


def get_tool(name: str) -> Tool | None:
    return _TOOLS.get(name)


def invoke_tool(name: str, params: dict, ctx: ToolContext) -> dict:
    """Invoke a tool by name, raising ToolError if it does not exist."""
    tool = get_tool(name)
    if tool is None:
        raise ToolError(f"unknown tool: {name}")
    return tool.invoke(params, ctx)


__all__ = [
    "all_tools",
    "tool_names",
    "offline_tool_names",
    "get_tool",
    "invoke_tool",
    "ToolError",
    "ToolContext",
]
