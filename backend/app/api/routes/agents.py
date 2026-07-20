"""Agent routes — CRUD, direct run, and execution history (tenant-scoped)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

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
    agent = Agent(
        org_id=current_user.org_id,
        name=payload.name,
        description=payload.description,
        system_prompt=payload.system_prompt,
    )
    agent.tools = payload.tools
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
    )


@router.get("/{agent_id}/executions", response_model=list[ExecutionOut])
def agent_executions(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_agent(db, current_user, agent_id)
    return (
        db.query(Execution)
        .filter(Execution.org_id == current_user.org_id, Execution.agent_id == agent_id)
        .order_by(Execution.id.desc())
        .all()
    )
