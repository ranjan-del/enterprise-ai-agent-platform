"""Auth + multi-tenancy tests: register, login, refresh, me, and isolation."""

from __future__ import annotations


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_returns_tokens(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"org_name": "Acme", "email": "a@acme.com", "password": "password123"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_and_me(auth_client):
    client, headers = auth_client
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@acme.com", "password": "password123"},
    )
    assert login.status_code == 200, login.text

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    data = me.json()
    assert data["user"]["email"] == "owner@acme.com"
    assert data["user"]["role"] == "owner"
    assert data["org"]["name"] == "Acme"


def test_login_wrong_password_rejected(auth_client):
    client, _ = auth_client
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@acme.com", "password": "wrongpass"},
    )
    assert resp.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_refresh_rotates_access_token(auth_client):
    client, _ = auth_client
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@acme.com", "password": "password123"},
    ).json()
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_tenant_isolation(client):
    # Two separate orgs cannot see each other's users.
    t1 = client.post(
        "/api/v1/auth/register",
        json={"org_name": "One", "email": "u@one.com", "password": "password123"},
    ).json()["access_token"]
    client.post(
        "/api/v1/auth/register",
        json={"org_name": "Two", "email": "u@two.com", "password": "password123"},
    )
    users = client.get("/api/v1/users", headers={"Authorization": f"Bearer {t1}"}).json()
    emails = {u["email"] for u in users}
    assert emails == {"u@one.com"}
