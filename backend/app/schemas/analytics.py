"""Pydantic schemas for analytics responses."""

from __future__ import annotations

from pydantic import BaseModel


class UsageMetrics(BaseModel):
    org_id: int
    users: int
    agents: int
    conversations: int
    messages: int
    executions: int
    tokens_used: int


class ExecutionAnalytics(BaseModel):
    total_executions: int
    completed: int
    failed: int
    tokens_used: int
    tool_usage: dict[str, int]
