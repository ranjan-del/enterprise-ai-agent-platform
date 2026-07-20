"""Analytics routes — usage and execution metrics for the caller's tenant."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_user
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.execution import Execution
from app.models.message import Message
from app.models.user import User
from app.schemas.analytics import ExecutionAnalytics, UsageMetrics

router = APIRouter()


@router.get("/usage", response_model=UsageMetrics)
def usage(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    org_id = current_user.org_id
    users = db.query(func.count(User.id)).filter(User.org_id == org_id).scalar() or 0
    agents = db.query(func.count(Agent.id)).filter(Agent.org_id == org_id).scalar() or 0
    conversations = (
        db.query(func.count(Conversation.id)).filter(Conversation.org_id == org_id).scalar() or 0
    )
    messages = (
        db.query(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.org_id == org_id)
        .scalar()
        or 0
    )
    executions = (
        db.query(func.count(Execution.id)).filter(Execution.org_id == org_id).scalar() or 0
    )
    tokens = (
        db.query(func.coalesce(func.sum(Execution.tokens_used), 0))
        .filter(Execution.org_id == org_id)
        .scalar()
        or 0
    )
    return UsageMetrics(
        org_id=org_id,
        users=users,
        agents=agents,
        conversations=conversations,
        messages=messages,
        executions=executions,
        tokens_used=int(tokens),
    )


@router.get("/executions", response_model=ExecutionAnalytics)
def executions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    org_id = current_user.org_id
    rows = db.query(Execution).filter(Execution.org_id == org_id).all()

    completed = sum(1 for r in rows if r.status == "completed")
    failed = sum(1 for r in rows if r.status != "completed")
    tokens = sum(r.tokens_used for r in rows)

    tool_usage: dict[str, int] = {}
    for r in rows:
        try:
            steps = json.loads(r.steps or "[]")
        except (ValueError, TypeError):
            steps = []
        for step in steps:
            if step.get("node") == "act" and step.get("detail", "").startswith("Executed '"):
                name = step["detail"].split("'", 2)[1]
                tool_usage[name] = tool_usage.get(name, 0) + 1

    return ExecutionAnalytics(
        total_executions=len(rows),
        completed=completed,
        failed=failed,
        tokens_used=tokens,
        tool_usage=tool_usage,
    )
