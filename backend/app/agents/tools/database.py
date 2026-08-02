"""Database tool: read-only, tenant-scoped queries over the caller's own data.

This is the "database" integration from the spec, done honestly: instead of
handing an agent raw SQL (which would be an injection and a tenancy hole in one
move), it exposes a small set of named, parameterised queries. Every one of
them filters on the ToolContext's org_id, and the per-user views also filter on
user_id, so an agent physically cannot phrase a query that reaches another
tenant.

Actions: ``stats``, ``conversations``, ``agents``, ``search_messages``.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func

from app.agents.tools.base import Tool, ToolContext, ToolError
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.execution import Execution
from app.models.message import Message
from app.models.user import User

_MAX_ROWS = 20


def _require_ctx(ctx: ToolContext) -> None:
    if ctx.db is None or ctx.org_id is None or ctx.user_id is None:
        raise ToolError("database tool requires an authenticated database context")


def _stats(ctx: ToolContext) -> dict[str, Any]:
    db = ctx.db
    conversations = (
        db.query(func.count(Conversation.id))
        .filter(Conversation.org_id == ctx.org_id, Conversation.user_id == ctx.user_id)
        .scalar()
        or 0
    )
    messages = (
        db.query(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.org_id == ctx.org_id, Conversation.user_id == ctx.user_id)
        .scalar()
        or 0
    )
    agents = db.query(func.count(Agent.id)).filter(Agent.org_id == ctx.org_id).scalar() or 0
    users = db.query(func.count(User.id)).filter(User.org_id == ctx.org_id).scalar() or 0
    executions = (
        db.query(func.count(Execution.id)).filter(Execution.org_id == ctx.org_id).scalar() or 0
    )
    return {
        "action": "stats",
        "stats": {
            "users": int(users),
            "agents": int(agents),
            "conversations": int(conversations),
            "messages": int(messages),
            "executions": int(executions),
        },
    }


def _conversations(ctx: ToolContext, limit: int) -> dict[str, Any]:
    rows = (
        ctx.db.query(Conversation)
        .filter(Conversation.org_id == ctx.org_id, Conversation.user_id == ctx.user_id)
        .order_by(Conversation.id.desc())
        .limit(limit)
        .all()
    )
    return {
        "action": "conversations",
        "conversations": [
            {"id": r.id, "title": r.title, "agent_id": r.agent_id} for r in rows
        ],
    }


def _agents(ctx: ToolContext, limit: int) -> dict[str, Any]:
    rows = (
        ctx.db.query(Agent)
        .filter(Agent.org_id == ctx.org_id)
        .order_by(Agent.id.asc())
        .limit(limit)
        .all()
    )
    return {
        "action": "agents",
        "agents": [{"id": r.id, "name": r.name, "tools": r.tools} for r in rows],
    }


def _search_messages(ctx: ToolContext, query: str, limit: int) -> dict[str, Any]:
    if not query:
        raise ToolError("search_messages requires a 'query'")
    # ILIKE-style contains, bound as a parameter (never string-formatted SQL).
    rows = (
        ctx.db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(
            Conversation.org_id == ctx.org_id,
            Conversation.user_id == ctx.user_id,
            Message.content.ilike(f"%{query}%"),
        )
        .order_by(Message.id.desc())
        .limit(limit)
        .all()
    )
    return {
        "action": "search_messages",
        "query": query,
        "matches": [
            {
                "id": r.id,
                "conversation_id": r.conversation_id,
                "role": r.role,
                "content": r.content,
            }
            for r in rows
        ],
    }


def _run(params: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    _require_ctx(ctx)
    action = str(params.get("action", "stats")).lower()
    try:
        limit = min(int(params.get("limit", 10)), _MAX_ROWS)
    except (TypeError, ValueError):
        raise ToolError("'limit' must be an integer")
    limit = max(limit, 1)

    if action == "stats":
        return _stats(ctx)
    if action == "conversations":
        return _conversations(ctx, limit)
    if action == "agents":
        return _agents(ctx, limit)
    if action == "search_messages":
        return _search_messages(ctx, str(params.get("query", "")).strip(), limit)
    raise ToolError(
        f"Unknown action '{action}' (use stats|conversations|agents|search_messages)"
    )


database_tool = Tool(
    name="database",
    description="Run read-only, tenant-scoped queries over your workspace data "
    "(counts, conversations, agents, message search).",
    parameters={
        "action": "One of stats | conversations | agents | search_messages",
        "query": "Text to search for (search_messages)",
        "limit": f"Maximum rows to return (default 10, max {_MAX_ROWS})",
    },
    run=_run,
    examples=['{"action": "stats"}', '{"action": "search_messages", "query": "invoice"}'],
)
