"""Conversation routes — create/list conversations and exchange messages.

Posting a user message runs the agent and returns the assistant's real reply
plus the tools used and step trace. All records are tenant-scoped.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_user
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.conversation import (
    ChatResponse,
    ConversationCreate,
    ConversationOut,
    MessageOut,
    SendMessageRequest,
)
from app.services.agent_service import run_turn

router = APIRouter()


def _get_owned_conversation(db: Session, user: User, conversation_id: int) -> Conversation:
    conv = db.get(Conversation, conversation_id)
    if conv is None or conv.org_id != user.org_id or conv.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conv


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Conversation)
        .filter(Conversation.org_id == current_user.org_id, Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.agent_id is not None:
        agent = db.get(Agent, payload.agent_id)
        if agent is None or agent.org_id != current_user.org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    conv = Conversation(
        org_id=current_user.org_id,
        user_id=current_user.id,
        agent_id=payload.agent_id,
        title=payload.title or "New conversation",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = _get_owned_conversation(db, current_user, conversation_id)
    return conv.messages


@router.post("/{conversation_id}/messages", response_model=ChatResponse)
def send_message(
    conversation_id: int,
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = _get_owned_conversation(db, current_user, conversation_id)
    agent = db.get(Agent, conv.agent_id) if conv.agent_id else None

    turn = run_turn(
        db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        conversation=conv,
        content=payload.content,
        agent=agent,
    )
    return ChatResponse(
        conversation_id=conv.id,
        user_message=turn.user_message,
        assistant_message=turn.assistant_message,
        tools_used=turn.tools_used,
        steps=turn.steps,
    )
