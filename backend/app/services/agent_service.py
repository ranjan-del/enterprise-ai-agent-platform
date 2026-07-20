"""Agent execution service — runs a turn and records persistence + trace.

Shared by the conversations (chat) and agents (run) routes so both produce the
same durable artefacts: a user message, an assistant message, and an Execution
row capturing the step trace, tools used, and token estimate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.agents.graph import run_agent
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.execution import Execution
from app.models.message import Message


@dataclass
class TurnResult:
    conversation: Conversation
    user_message: Message
    assistant_message: Message
    execution: Execution
    tools_used: list[str]
    steps: list[dict]


def run_turn(
    db: Session,
    *,
    org_id: int,
    user_id: int,
    conversation: Conversation,
    content: str,
    agent: Agent | None = None,
) -> TurnResult:
    """Execute one conversational turn and persist all resulting records."""
    agent_name = agent.name if agent else "Assistant"
    enabled_tools = agent.tools if agent else None

    user_msg = Message(conversation_id=conversation.id, role="user", content=content)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    result = run_agent(
        db=db,
        org_id=org_id,
        user_id=user_id,
        conversation_id=conversation.id,
        message=content,
        agent_name=agent_name,
        enabled_tools=enabled_tools,
    )

    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=result.reply,
        tool_calls=json.dumps(result.tools_used),
    )
    db.add(assistant_msg)

    execution = Execution(
        org_id=org_id,
        agent_id=agent.id if agent else None,
        conversation_id=conversation.id,
        status="completed",
        steps=json.dumps(result.steps),
        tokens_used=result.tokens_used,
    )
    db.add(execution)

    # Auto-title a fresh conversation from its first user message.
    if conversation.title == "New conversation":
        conversation.title = content[:60]

    db.commit()
    db.refresh(assistant_msg)
    db.refresh(execution)

    return TurnResult(
        conversation=conversation,
        user_message=user_msg,
        assistant_message=assistant_msg,
        execution=execution,
        tools_used=result.tools_used,
        steps=result.steps,
    )
