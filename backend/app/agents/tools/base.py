"""Tool abstraction shared by every offline tool.

A ``Tool`` bundles a name, human description, a small parameter schema (for the
API + UI), and a ``run`` callable. Tools receive a :class:`ToolContext` giving
them scoped access to the database and the current tenant/user, so tools like
``notes`` can persist data without any external service.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session


@dataclass
class ToolContext:
    """Runtime context passed to a tool invocation."""

    db: Optional[Session] = None
    org_id: Optional[int] = None
    user_id: Optional[int] = None


class ToolError(Exception):
    """Raised when a tool cannot fulfil a request (bad input, etc.)."""


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, str]                     # param -> description
    run: Callable[[dict[str, Any], ToolContext], dict[str, Any]]
    examples: list[str] = field(default_factory=list)
    # True for tools that call the internet. Surfaced through the API so the UI
    # can tell users which tools stop working in a fully offline install.
    requires_network: bool = False

    def invoke(self, params: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
        return self.run(params or {}, ctx)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "examples": self.examples,
            "requires_network": self.requires_network,
        }
