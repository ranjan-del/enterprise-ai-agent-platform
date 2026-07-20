"""Shared / generic Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MessageResponse(BaseModel):
    detail: str


class UserCreate(BaseModel):
    """Create a user within the caller's organization."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str
    is_active: bool
    org_id: int
