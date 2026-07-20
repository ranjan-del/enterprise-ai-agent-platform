"""Shared pytest fixtures: an isolated app + client backed by a temp SQLite DB.

Each test module gets a fresh database file and a TestClient with the app's
``get_db`` dependency overridden to use it, so tests never touch a real service.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

import pytest

# Ensure a deterministic, offline configuration BEFORE importing the app.
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("SEED_DEMO_DATA", "false")
os.environ.setdefault("REDIS_URL", "")


@pytest.fixture()
def client() -> Iterator["TestClient"]:  # noqa: F821 (forward ref for type only)
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.models  # noqa: F401 -- register models
    from app.db.session import Base, get_db
    from app.main import app

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(
        f"sqlite:///{path}", connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()
    os.unlink(path)


@pytest.fixture()
def auth_client(client):
    """A client with a registered + logged-in org owner; returns (client, headers)."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"org_name": "Acme", "email": "owner@acme.com", "password": "password123"},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return client, {"Authorization": f"Bearer {token}"}
