"""Pydantic schemas for agents, tools, and agent execution."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    system_prompt: str = ""
    tools: list[str] = Field(default_factory=list)


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    system_prompt: str | None = None
    tools: list[str] | None = None


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    system_prompt: str
    tools: list[str]
    org_id: int


class ToolOut(BaseModel):
    name: str
    description: str
    parameters: dict[str, str]
    examples: list[str] = Field(default_factory=list)


class ToolInvokeRequest(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)


class ToolInvokeResponse(BaseModel):
    tool: str
    result: dict[str, Any]


class AgentRunRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: int | None = None


class ExecutionStep(BaseModel):
    node: str
    detail: str


class AgentRunResponse(BaseModel):
    conversation_id: int
    reply: str
    steps: list[ExecutionStep]
    tools_used: list[str]
    execution_id: int


class ExecutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int | None
    conversation_id: int | None
    status: str
    tokens_used: int
    started_at: datetime
    finished_at: datetime
