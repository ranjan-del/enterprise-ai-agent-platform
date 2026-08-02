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
# Settings are cached with lru_cache, so these must be set at import time.
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("SEED_DEMO_DATA", "false")
os.environ.setdefault("REDIS_URL", "")
# Network tools stay off: the suite must pass with no internet access.
os.environ.setdefault("ALLOW_NETWORK_TOOLS", "false")
# Keep the file-system tool's sandbox out of the working tree.
os.environ.setdefault("WORKSPACE_ROOT", tempfile.mkdtemp(prefix="eap-workspace-"))


@pytest.fixture(autouse=True)
def isolated_workspace(tmp_path, monkeypatch) -> None:
    """Give every test its own file-system sandbox root.

    The sandbox is keyed by (org id, user id) and every test starts from a fresh
    database, so org 1 / user 1 is reused constantly. Sharing one root across
    the session would let a file written by one test show up in the next one's
    directory listing. A per-test root keeps the tests honest without weakening
    the production layout.
    """
    from app.core import config

    monkeypatch.setattr(config.settings, "WORKSPACE_ROOT", str(tmp_path / "workspace"))


@pytest.fixture()
def client() -> Iterator["TestClient"]:  # noqa: F821 (forward ref for type only)
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.models  # noqa: F401 -- register models
    from app.cache.redis import reset_session_cache
    from app.db.session import Base, get_db
    from app.main import app

    # The session cache is a process-wide singleton keyed by (org, conversation)
    # ids, which restart at 1 in every temp database. Reset it so one test's
    # short-term memory cannot appear in the next test's conversation.
    reset_session_cache()

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
def register_org(client):
    """Factory: create an org + owner and return their auth headers.

    Tenancy tests need two independent tenants inside one database, so the
    factory shape matters more than a single ready-made fixture.
    """

    def _register(org_name: str, email: str, password: str = "password123") -> dict[str, str]:
        resp = client.post(
            "/api/v1/auth/register",
            json={"org_name": org_name, "email": email, "password": password},
        )
        assert resp.status_code == 201, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _register


@pytest.fixture()
def auth_client(client, register_org):
    """A client with a registered + logged-in org owner; returns (client, headers)."""
    return client, register_org("Acme", "owner@acme.com")


@pytest.fixture()
def two_orgs(client, register_org):
    """Two fully separate tenants; returns (client, headers_a, headers_b)."""
    a = register_org("Alpha", "owner@alpha.com")
    b = register_org("Beta", "owner@beta.com")
    return client, a, b
