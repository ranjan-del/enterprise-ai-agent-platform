"""Agent execution service — runs a turn and records persistence + trace.

Shared by the conversations (chat + SSE) and agents (run) routes so every entry
point produces the same durable artefacts: a user message, an assistant
message, indexed vector memory, and an Execution row capturing the step trace,
tools used and token estimate.

It also owns the human-approval lifecycle: a paused run is stored as an
Execution with ``status="awaiting_approval"`` plus the pending tool call, and
``resolve_execution`` either replays that exact call or records a rejection.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.agents.graph import AgentResult, Teammate, run_agent, stream_agent
from app.agents.memory.persistent import PersistentMemory
from app.agents.memory.vector import TenantVectorMemory
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.execution import AWAITING_APPROVAL, COMPLETED, REJECTED, Execution
from app.models.message import Message


@dataclass
class TurnResult:
    conversation: Conversation
    user_message: Message
    assistant_message: Message
    execution: Execution
    tools_used: list[str]
    steps: list[dict]
    status: str = COMPLETED


def load_teammates(db: Session, agent: Agent | None) -> list[Teammate]:
    """Resolve an agent's configured teammates, re-checking the org boundary.

    The org filter is applied here, not only when the ids are saved, so that a
    stale or hand-edited teammate id can never pull another tenant's agent into
    a run.
    """
    if agent is None or not agent.teammates:
        return []
    rows = (
        db.query(Agent)
        .filter(Agent.id.in_(agent.teammates), Agent.org_id == agent.org_id, Agent.id != agent.id)
        .order_by(Agent.id.asc())
        .all()
    )
    return [Teammate(id=r.id, name=r.name, tools=r.tools) for r in rows]


def _persist_outcome(
    db: Session,
    *,
    org_id: int,
    user_id: int,
    conversation: Conversation,
    content: str,
    agent: Agent | None,
    result: AgentResult,
) -> TurnResult:
    """Store both sides of the turn, index them, and write the Execution row.

    Both messages are written *after* the graph has finished, never before, so
    a client that hangs up mid-stream leaves no half-turn behind: either the
    whole exchange is recorded or none of it is.
    """
    memory = PersistentMemory(db, conversation.id)
    user_message = memory.add("user", content)
    assistant_msg = memory.add(
        "assistant", result.reply, tool_calls=json.dumps(result.tools_used)
    )

    # Vector memory indexes the assistant side too, so later turns can recall
    # answers the agent gave, not only questions the user asked.
    TenantVectorMemory(db, org_id, user_id).index(
        result.reply, kind="message", conversation_id=conversation.id
    )

    execution = Execution(
        org_id=org_id,
        user_id=user_id,
        agent_id=agent.id if agent else None,
        conversation_id=conversation.id,
        status=result.status,
        steps=json.dumps(result.steps),
        tokens_used=result.tokens_used,
        pending_action=json.dumps(result.pending_action) if result.pending_action else None,
    )
    db.add(execution)

    # Auto-title a fresh conversation from its first user message.
    if conversation.title == "New conversation":
        conversation.title = user_message.content[:60]
    # Touch the thread so the sidebar can order conversations by real activity.
    # ``onupdate`` only fires when a column actually changes, and a plain reply
    # changes nothing on the conversation row itself.
    conversation.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(assistant_msg)
    db.refresh(execution)

    return TurnResult(
        conversation=conversation,
        user_message=user_message,
        assistant_message=assistant_msg,
        execution=execution,
        tools_used=result.tools_used,
        steps=result.steps,
        status=result.status,
    )


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
    result = run_agent(
        db=db,
        org_id=org_id,
        user_id=user_id,
        conversation_id=conversation.id,
        message=content,
        agent_name=agent.name if agent else "Assistant",
        enabled_tools=agent.tools if agent else None,
        teammates=load_teammates(db, agent),
        requires_approval=bool(agent.requires_approval) if agent else False,
    )
    return _persist_outcome(
        db,
        org_id=org_id,
        user_id=user_id,
        conversation=conversation,
        content=content,
        agent=agent,
        result=result,
    )


def stream_turn(
    db: Session,
    *,
    org_id: int,
    user_id: int,
    conversation: Conversation,
    content: str,
    agent: Agent | None = None,
) -> Iterator[dict]:
    """Yield JSON-ready events for one turn: a step per node, then the result.

    The generator drives the same graph as :func:`run_turn`. Persistence still
    happens once, after the final node, so a client that disconnects mid-stream
    does not leave half a turn in the database.
    """
    final: AgentResult | None = None

    for event in stream_agent(
        db=db,
        org_id=org_id,
        user_id=user_id,
        conversation_id=conversation.id,
        message=content,
        agent_name=agent.name if agent else "Assistant",
        enabled_tools=agent.tools if agent else None,
        teammates=load_teammates(db, agent),
        requires_approval=bool(agent.requires_approval) if agent else False,
    ):
        if event.type == "step":
            yield {"event": "step", "node": event.node, "detail": event.detail}
        else:
            final = event.result

    if final is None:  # pragma: no cover - stream_agent always ends with a result
        raise RuntimeError("agent stream ended without a result event")

    turn = _persist_outcome(
        db,
        org_id=org_id,
        user_id=user_id,
        conversation=conversation,
        content=content,
        agent=agent,
        result=final,
    )
    yield {
        "event": "result",
        "conversation_id": conversation.id,
        "message_id": turn.assistant_message.id,
        "execution_id": turn.execution.id,
        "status": turn.status,
        "tools_used": turn.tools_used,
        "reply": turn.assistant_message.content,
    }


def resolve_execution(db: Session, execution: Execution, *, approve: bool) -> Execution:
    """Approve or reject a paused run and record the outcome.

    On approval the stored tool call is replayed verbatim (``forced_intent``),
    so what runs is exactly what the user saw in the approval prompt. On
    rejection nothing is executed and the agent says so in the thread.
    """
    if execution.status != AWAITING_APPROVAL or not execution.pending_action:
        raise ValueError("execution is not awaiting approval")

    action = json.loads(execution.pending_action)
    conversation = db.get(Conversation, execution.conversation_id)
    if conversation is None:
        raise ValueError("the conversation for this execution no longer exists")
    agent = db.get(Agent, execution.agent_id) if execution.agent_id else None
    user_id = execution.user_id or conversation.user_id
    steps = json.loads(execution.steps or "[]")

    if not approve:
        PersistentMemory(db, conversation.id).add(
            "assistant", f"Understood, I will not run **{action['tool']}**."
        )
        steps.append({"node": "approval", "detail": "Rejected by the user; no tool was executed."})
        execution.steps = json.dumps(steps)
        execution.status = REJECTED
        execution.pending_action = None
        execution.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(execution)
        return execution

    result = run_agent(
        db=db,
        org_id=execution.org_id,
        user_id=user_id,
        conversation_id=conversation.id,
        message=action["message"],
        agent_name=agent.name if agent else "Assistant",
        enabled_tools=agent.tools if agent else None,
        teammates=load_teammates(db, agent),
        requires_approval=False,
        pre_approved=True,
        forced_intent=(action["tool"], action["params"]),
        record_user_turn=False,
    )
    PersistentMemory(db, conversation.id).add(
        "assistant", result.reply, tool_calls=json.dumps(result.tools_used)
    )

    steps.append({"node": "approval", "detail": "Approved by the user; replaying the tool call."})
    steps.extend(result.steps)
    execution.steps = json.dumps(steps)
    execution.status = COMPLETED
    execution.pending_action = None
    execution.tokens_used += result.tokens_used
    execution.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(execution)
    return execution
