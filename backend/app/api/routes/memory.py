"""Memory routes: inspect and edit what the agent remembers about you.

Exposes the four layers the runtime uses:

* user memory     -> ``/memory/facts`` (list, add, delete)
* vector memory   -> ``/memory/recall`` (semantic search over indexed text)
* session memory  -> ``/memory/session/{conversation_id}`` (short-term window)
* persistent      -> counted in ``/memory/overview``; the full history is served
                     by the conversations routes

Everything is scoped to the caller's org AND user id, so memory never crosses a
tenant boundary or another person in the same tenant.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agents.memory.session import SessionMemory
from app.agents.memory.user import UserMemory
from app.agents.memory.vector import TenantVectorMemory
from app.db.session import get_db
from app.deps import get_current_user
from app.models.conversation import Conversation
from app.models.memory_document import MemoryDocument
from app.models.message import Message
from app.models.user import User
from app.schemas.memory import (
    FactCreate,
    FactOut,
    MemoryOverview,
    RecallHit,
    RecallResponse,
    SessionTurn,
    SessionWindow,
)

router = APIRouter()


def _owned_conversation(db: Session, user: User, conversation_id: int) -> Conversation:
    conv = db.get(Conversation, conversation_id)
    if conv is None or conv.org_id != user.org_id or conv.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conv


@router.get("/facts", response_model=list[FactOut])
def list_facts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return UserMemory(db, current_user.org_id, current_user.id).rows()


@router.post("/facts", response_model=FactOut, status_code=status.HTTP_201_CREATED)
def add_fact(
    payload: FactCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memory = UserMemory(db, current_user.org_id, current_user.id)
    row = memory.add(payload.fact.strip())
    # Keep the vector layer in step so a manually added fact is recallable too.
    TenantVectorMemory(db, current_user.org_id, current_user.id).index(row.fact, kind="fact")
    return row


@router.delete("/facts/{fact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fact(
    fact_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted = UserMemory(db, current_user.org_id, current_user.id).delete(fact_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fact not found")


@router.get("/recall", response_model=RecallResponse)
def recall(
    q: str = Query(min_length=1, description="Text to search memory for"),
    k: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Semantic-ish recall over everything indexed for this user."""
    hits = TenantVectorMemory(db, current_user.org_id, current_user.id).search(q, k=k)
    return RecallResponse(
        query=q,
        hits=[RecallHit(id=h.id, kind=h.kind, text=h.text, score=round(h.score, 4)) for h in hits],
    )


@router.get("/session/{conversation_id}", response_model=SessionWindow)
def session_window(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The rolling short-term window held in Redis (or the in-process cache)."""
    conv = _owned_conversation(db, current_user, conversation_id)
    turns = SessionMemory(current_user.org_id, conv.id).history()
    return SessionWindow(
        conversation_id=conv.id,
        turns=[SessionTurn(role=t.get("role", ""), content=t.get("content", "")) for t in turns],
    )


@router.get("/overview", response_model=MemoryOverview)
def overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    facts = len(UserMemory(db, current_user.org_id, current_user.id).rows())
    documents = (
        db.query(func.count(MemoryDocument.id))
        .filter(
            MemoryDocument.org_id == current_user.org_id,
            MemoryDocument.user_id == current_user.id,
        )
        .scalar()
        or 0
    )
    messages = (
        db.query(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(
            Conversation.org_id == current_user.org_id,
            Conversation.user_id == current_user.id,
        )
        .scalar()
        or 0
    )
    return MemoryOverview(facts=facts, documents=int(documents), messages=int(messages))
