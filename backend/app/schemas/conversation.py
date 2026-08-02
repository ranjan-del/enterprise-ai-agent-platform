"""Pydantic schemas for conversations and messages."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    title: str | None = None
    agent_id: int | None = None


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    agent_id: int | None
    user_id: int
    org_id: int
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1)


class ChatResponse(BaseModel):
    """Result of posting a user message: both turns plus the run trace."""

    conversation_id: int
    user_message: MessageOut
    assistant_message: MessageOut
    tools_used: list[str]
    steps: list[dict]
    # "completed", or "awaiting_approval" when the agent paused for a human.
    status: str = "completed"
