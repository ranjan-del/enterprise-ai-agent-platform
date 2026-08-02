"""Pydantic schemas for the memory API (facts, session window, recall)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fact: str
    created_at: datetime


class FactCreate(BaseModel):
    fact: str = Field(min_length=1, max_length=500)


class SessionTurn(BaseModel):
    role: str
    content: str


class SessionWindow(BaseModel):
    """The short-term window a conversation currently holds in the cache."""

    conversation_id: int
    turns: list[SessionTurn]


class RecallHit(BaseModel):
    id: int
    kind: str
    text: str
    score: float


class RecallResponse(BaseModel):
    query: str
    hits: list[RecallHit]


class MemoryOverview(BaseModel):
    """Counts per layer, for the Memory page."""

    facts: int
    documents: int
    messages: int
