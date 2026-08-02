"""Agent routes — CRUD, direct run, and execution history (tenant-scoped)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.routes.executions import scope_executions
from app.db.session import get_db
from app.deps import get_current_user, require_role
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.execution import Execution
from app.models.role import Role
from app.models.user import User
from app.agents.tools.registry import get_tool
from app.schemas.agent import (
    AgentCreate,
    AgentOut,
    AgentRunRequest,
    AgentRunResponse,
    AgentUpdate,
    ExecutionOut,
    ExecutionStep,
)
from app.services.agent_service import run_turn

router = APIRouter()


def _validate_tools(tools: list[str]) -> None:
    unknown = [t for t in tools if get_tool(t) is None]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown tools: {', '.join(unknown)}",
        )


def _validate_teammates(db: Session, org_id: int, ids: list[int], self_id: int | None = None) -> None:
    """Reject teammate ids that are not agents of this org (or are the agent itself).

    Delegation is the one feature that lets one agent act through another, so
    the org check happens here at write time and again at run time in
    ``agent_service.load_teammates``.
    """
    unique = {int(i) for i in ids}
    if self_id is not None and self_id in unique:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An agent cannot be its own teammate",
        )
    if not unique:
        return
    found = {
        row.id
        for row in db.query(Agent.id).filter(Agent.id.in_(unique), Agent.org_id == org_id).all()
    }
    missing = sorted(unique - found)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown teammate agents: {', '.join(str(m) for m in missing)}",
        )


def _get_owned_agent(db: Session, user: User, agent_id: int) -> Agent:
    agent = db.get(Agent, agent_id)
    if agent is None or agent.org_id != user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.get("", response_model=list[AgentOut])
def list_agents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Agent)
        .filter(Agent.org_id == current_user.org_id)
        .order_by(Agent.id.asc())
        .all()
    )


@router.post("", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: AgentCreate,
    current_user: User = Depends(require_role(Role.OWNER.value, Role.ADMIN.value)),
    db: Session = Depends(get_db),
):
    _validate_tools(payload.tools)
    _validate_teammates(db, current_user.org_id, payload.teammates)
    agent = Agent(
        org_id=current_user.org_id,
        name=payload.name,
        description=payload.description,
        system_prompt=payload.system_prompt,
        requires_approval=payload.requires_approval,
    )
    agent.tools = payload.tools
    agent.teammates = payload.teammates
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_agent(db, current_user, agent_id)


@router.patch("/{agent_id}", response_model=AgentOut)
def update_agent(
    agent_id: int,
    payload: AgentUpdate,
    current_user: User = Depends(require_role(Role.OWNER.value, Role.ADMIN.value)),
    db: Session = Depends(get_db),
):
    agent = _get_owned_agent(db, current_user, agent_id)
    if payload.name is not None:
        agent.name = payload.name
    if payload.description is not None:
        agent.description = payload.description
    if payload.system_prompt is not None:
        agent.system_prompt = payload.system_prompt
    if payload.tools is not None:
        _validate_tools(payload.tools)
        agent.tools = payload.tools
    if payload.teammates is not None:
        _validate_teammates(db, current_user.org_id, payload.teammates, self_id=agent.id)
        agent.teammates = payload.teammates
    if payload.requires_approval is not None:
        agent.requires_approval = payload.requires_approval
    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: int,
    current_user: User = Depends(require_role(Role.OWNER.value, Role.ADMIN.value)),
    db: Session = Depends(get_db),
):
    agent = _get_owned_agent(db, current_user, agent_id)
    db.delete(agent)
    db.commit()


@router.post("/{agent_id}/run", response_model=AgentRunResponse)
def run_agent_endpoint(
    agent_id: int,
    payload: AgentRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = _get_owned_agent(db, current_user, agent_id)

    if payload.conversation_id is not None:
        conv = db.get(Conversation, payload.conversation_id)
        if conv is None or conv.org_id != current_user.org_id or conv.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    else:
        conv = Conversation(
            org_id=current_user.org_id,
            user_id=current_user.id,
            agent_id=agent.id,
            title="New conversation",
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    turn = run_turn(
        db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        conversation=conv,
        content=payload.message,
        agent=agent,
    )
    return AgentRunResponse(
        conversation_id=conv.id,
        reply=turn.assistant_message.content,
        steps=[ExecutionStep(**s) for s in turn.steps],
        tools_used=turn.tools_used,
        execution_id=turn.execution.id,
        status=turn.status,
    )


@router.get("/{agent_id}/executions", response_model=list[ExecutionOut])
def agent_executions(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_agent(db, current_user, agent_id)
    # Same visibility rule as /executions: members see their own runs, owners
    # and admins see everyone's. Defined once, in the executions module.
    query = scope_executions(db.query(Execution), current_user)
    return query.filter(Execution.agent_id == agent_id).order_by(Execution.id.desc()).all()
