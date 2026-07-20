"""Utility tools that run fully offline: ``echo`` and ``time``."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.agents.tools.base import Tool, ToolContext


def _echo(params: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    text = params.get("text", "")
    return {"echo": str(text)}


def _time(params: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "iso": now.isoformat(),
        "unix": int(now.timestamp()),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S UTC"),
    }


echo_tool = Tool(
    name="echo",
    description="Return the given text unchanged (useful for testing tool calls).",
    parameters={"text": "The text to echo back"},
    run=_echo,
    examples=['{"text": "hello world"}'],
)

time_tool = Tool(
    name="time",
    description="Return the current UTC date and time.",
    parameters={},
    run=_time,
    examples=["{}"],
)
