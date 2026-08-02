"""Execution routes: run history and human-approval decisions.

``/agents/{id}/executions`` only shows runs of one agent, which misses every
chat turn that had no agent attached. These routes are the complete view the
Logs page uses, plus the approve/reject endpoints that resume a paused run.

Visibility has two levels inside a tenant. A run's trace contains the user's own
words, so a plain member only ever sees the runs they triggered; owners and
admins see the whole organization, which is what makes the Logs page useful as
an audit view. The org filter applies to everyone, always.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Query as SAQuery
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_user
from app.models.execution import Execution
from app.models.role import Role
from app.models.user import User
from app.schemas.agent import ExecutionDetail, ExecutionOut, ExecutionStep
from app.services.agent_service import resolve_execution

router = APIRouter()

_ORG_WIDE_ROLES = (Role.OWNER.value, Role.ADMIN.value)


def can_view_execution(user: User, execution: Execution) -> bool:
    """True when ``user`` may see this run (own run, or they administer the org)."""
    if execution.org_id != user.org_id:
        return False
    return user.role in _ORG_WIDE_ROLES or execution.user_id == user.id


def scope_executions(query: SAQuery, user: User) -> SAQuery:
    """Narrow an Execution query to the rows ``user`` is allowed to read."""
    query = query.filter(Execution.org_id == user.org_id)
    if user.role not in _ORG_WIDE_ROLES:
        query = query.filter(Execution.user_id == user.id)
    return query


def _get_owned_execution(db: Session, user: User, execution_id: int) -> Execution:
    execution = db.get(Execution, execution_id)
    if execution is None or not can_view_execution(user, execution):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    return execution


def _to_detail(execution: Execution) -> ExecutionDetail:
    try:
        steps = json.loads(execution.steps or "[]")
    except (ValueError, TypeError):
        steps = []
    pending = json.loads(execution.pending_action) if execution.pending_action else None
    return ExecutionDetail(
        id=execution.id,
        agent_id=execution.agent_id,
        conversation_id=execution.conversation_id,
        status=execution.status,
        tokens_used=execution.tokens_used,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        steps=[ExecutionStep(**s) for s in steps if isinstance(s, dict)],
        pending_action=pending,
    )


@router.get("", response_model=list[ExecutionOut])
def list_executions(
    limit: int = Query(default=50, ge=1, le=200),
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Runs visible to the caller, newest first."""
    query = scope_executions(db.query(Execution), current_user)
    if status_filter:
        query = query.filter(Execution.status == status_filter)
    return query.order_by(Execution.id.desc()).limit(limit).all()


@router.get("/{execution_id}", response_model=ExecutionDetail)
def get_execution(
    execution_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """One run with its full plan/memory/act/reflect/respond trace."""
    return _to_detail(_get_owned_execution(db, current_user, execution_id))


@router.post("/{execution_id}/approve", response_model=ExecutionDetail)
def approve_execution(
    execution_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve a paused run: the stored tool call is replayed verbatim."""
    execution = _get_owned_execution(db, current_user, execution_id)
    try:
        resolved = resolve_execution(db, execution, approve=True)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return _to_detail(resolved)


@router.post("/{execution_id}/reject", response_model=ExecutionDetail)
def reject_execution(
    execution_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reject a paused run: nothing is executed and the thread records it."""
    execution = _get_owned_execution(db, current_user, execution_id)
    try:
        resolved = resolve_execution(db, execution, approve=False)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return _to_detail(resolved)
