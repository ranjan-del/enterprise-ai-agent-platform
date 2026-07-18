"""Application entrypoint for the Enterprise AI Agent Platform backend.

FastAPI app factory + health check. Router registration wires up the
API surface described in MEMORY.md (auth, orgs, users, conversations,
agents, tools, analytics).
"""
from fastapi import FastAPI

# TODO: checklist "Backend: FastAPI services" — import and mount routers below.
from app.api.routes import (
    agents,
    analytics,
    auth,
    conversations,
    orgs,
    tools,
    users,
)

app = FastAPI(
    title="Enterprise AI Agent Platform",
    description="Multi-tenant ChatGPT Workspace — FastAPI + LangGraph backend.",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
async def health() -> dict:
    """Liveness probe used by docker-compose / Cloud Run health checks."""
    return {"status": "ok"}


# TODO: checklist "API documentation" — group routers under /api/v1 prefix.
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(orgs.router, prefix="/api/v1/orgs", tags=["orgs"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(
    conversations.router, prefix="/api/v1/conversations", tags=["conversations"]
)
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(tools.router, prefix="/api/v1/tools", tags=["tools"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])


# TODO: checklist "Agent runtime on LangGraph" — add startup/shutdown hooks
# to initialize the LangGraph runtime, Redis pool, and DB engine.
