"""FastAPI application entrypoint for the Enterprise AI Agent Platform.

Wires configuration, database, CORS, and the versioned API routers. On startup
it creates tables and seeds a demo tenant so the platform is usable with zero
external services and zero API keys.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 -- register all models on Base.metadata
from app.api.routes import (
    agents,
    analytics,
    auth,
    conversations,
    executions,
    memory,
    orgs,
    tools,
    users,
)
from app.core.config import settings
from app.db.session import Base, engine
from app.services.seed import seed_demo_data

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_demo_data()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Multi-tenant AI agent workspace: auth, agents, tools, memory, analytics.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok"}


app.include_router(auth.router, prefix=f"{API_PREFIX}/auth", tags=["auth"])
app.include_router(orgs.router, prefix=f"{API_PREFIX}/orgs", tags=["orgs"])
app.include_router(users.router, prefix=f"{API_PREFIX}/users", tags=["users"])
app.include_router(conversations.router, prefix=f"{API_PREFIX}/conversations", tags=["conversations"])
app.include_router(agents.router, prefix=f"{API_PREFIX}/agents", tags=["agents"])
app.include_router(executions.router, prefix=f"{API_PREFIX}/executions", tags=["executions"])
app.include_router(memory.router, prefix=f"{API_PREFIX}/memory", tags=["memory"])
app.include_router(tools.router, prefix=f"{API_PREFIX}/tools", tags=["tools"])
app.include_router(analytics.router, prefix=f"{API_PREFIX}/analytics", tags=["analytics"])
