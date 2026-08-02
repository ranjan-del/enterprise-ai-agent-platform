"""Multi-tenant isolation tests: the single most important property here.

Every endpoint that takes an id is probed with an id belonging to *another*
tenant. The expected answer is always 404 (or 403 for the org endpoint, which
deliberately admits the resource exists but is not yours). Anything that
returns 200 here is a data breach, so these tests are written as a sweep rather
than as one-off cases: adding a route without adding it to this file should
feel wrong.
"""

from __future__ import annotations


def _make_agent(client, headers, name="Helper", tools=None):
    resp = client.post(
        "/api/v1/agents",
        json={"name": name, "tools": tools if tools is not None else ["calculator"]},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _make_conversation(client, headers, agent_id=None):
    resp = client.post("/api/v1/conversations", json={"agent_id": agent_id}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _chat(client, headers, conversation_id, content):
    resp = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": content},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_cannot_read_another_orgs_agent(two_orgs):
    client, alpha, beta = two_orgs
    agent_id = _make_agent(client, alpha)

    assert client.get(f"/api/v1/agents/{agent_id}", headers=beta).status_code == 404
    assert client.patch(
        f"/api/v1/agents/{agent_id}", json={"name": "Hijacked"}, headers=beta
    ).status_code == 404
    assert client.delete(f"/api/v1/agents/{agent_id}", headers=beta).status_code == 404
    assert client.post(
        f"/api/v1/agents/{agent_id}/run", json={"message": "2 + 2"}, headers=beta
    ).status_code == 404
    assert client.get(f"/api/v1/agents/{agent_id}/executions", headers=beta).status_code == 404

    # And the owner still can.
    assert client.get(f"/api/v1/agents/{agent_id}", headers=alpha).status_code == 200


def test_agent_list_never_crosses_tenants(two_orgs):
    client, alpha, beta = two_orgs
    _make_agent(client, alpha, name="AlphaBot")
    _make_agent(client, beta, name="BetaBot")

    names_a = {a["name"] for a in client.get("/api/v1/agents", headers=alpha).json()}
    names_b = {a["name"] for a in client.get("/api/v1/agents", headers=beta).json()}
    assert names_a == {"AlphaBot"}
    assert names_b == {"BetaBot"}


def test_cannot_read_another_orgs_conversation_or_messages(two_orgs):
    client, alpha, beta = two_orgs
    conv = _make_conversation(client, alpha)
    _chat(client, alpha, conv, "remember that alpha's launch code is hunter2")

    assert client.get(f"/api/v1/conversations/{conv}/messages", headers=beta).status_code == 404
    assert client.post(
        f"/api/v1/conversations/{conv}/messages", json={"content": "hi"}, headers=beta
    ).status_code == 404
    assert client.post(
        f"/api/v1/conversations/{conv}/messages/stream", json={"content": "hi"}, headers=beta
    ).status_code == 404
    assert client.get("/api/v1/conversations", headers=beta).json() == []


def test_cannot_read_another_orgs_execution_or_approve_it(two_orgs):
    client, alpha, beta = two_orgs
    agent_id = _make_agent(client, alpha, tools=["calculator"])
    run = client.post(
        f"/api/v1/agents/{agent_id}/run", json={"message": "2 + 2"}, headers=alpha
    ).json()
    execution_id = run["execution_id"]

    assert client.get(f"/api/v1/executions/{execution_id}", headers=beta).status_code == 404
    assert client.post(f"/api/v1/executions/{execution_id}/approve", headers=beta).status_code == 404
    assert client.post(f"/api/v1/executions/{execution_id}/reject", headers=beta).status_code == 404
    assert client.get("/api/v1/executions", headers=beta).json() == []
    assert client.get(f"/api/v1/executions/{execution_id}", headers=alpha).status_code == 200


def test_cannot_read_another_orgs_users_or_org(two_orgs):
    client, alpha, beta = two_orgs
    alpha_user = client.get("/api/v1/auth/me", headers=alpha).json()
    user_id = alpha_user["user"]["id"]
    org_id = alpha_user["org"]["id"]

    assert client.get(f"/api/v1/users/{user_id}", headers=beta).status_code == 404
    assert client.get(f"/api/v1/orgs/{org_id}", headers=beta).status_code == 403
    assert len(client.get("/api/v1/orgs", headers=beta).json()) == 1


def test_notes_and_files_are_not_shared_between_tenants(two_orgs):
    client, alpha, beta = two_orgs
    created = client.post(
        "/api/v1/tools/notes/invoke",
        json={"params": {"action": "create", "title": "Secret", "body": "alpha only"}},
        headers=alpha,
    ).json()["result"]["note"]

    # Beta cannot list it...
    beta_notes = client.post(
        "/api/v1/tools/notes/invoke", json={"params": {"action": "list"}}, headers=beta
    ).json()["result"]["notes"]
    assert beta_notes == []

    # ...and cannot fetch it by id either.
    got = client.post(
        "/api/v1/tools/notes/invoke",
        json={"params": {"action": "get", "id": created["id"]}},
        headers=beta,
    )
    assert got.status_code == 400
    assert "not found" in got.json()["detail"]

    client.post(
        "/api/v1/tools/filesystem/invoke",
        json={"params": {"action": "write", "path": "plan.md", "content": "alpha roadmap"}},
        headers=alpha,
    )
    beta_files = client.post(
        "/api/v1/tools/filesystem/invoke", json={"params": {"action": "list"}}, headers=beta
    ).json()["result"]["files"]
    assert beta_files == []


def test_memory_layers_are_per_tenant(two_orgs):
    client, alpha, beta = two_orgs
    conv = _make_conversation(client, alpha)
    _chat(client, alpha, conv, "remember that the alpha deploy key is in the vault")

    assert client.get("/api/v1/memory/facts", headers=beta).json() == []
    recall = client.get("/api/v1/memory/recall", params={"q": "deploy key"}, headers=beta).json()
    assert recall["hits"] == []
    assert client.get(f"/api/v1/memory/session/{conv}", headers=beta).status_code == 404

    # Alpha itself does recall it, proving the query works and is just scoped.
    alpha_recall = client.get(
        "/api/v1/memory/recall", params={"q": "deploy key"}, headers=alpha
    ).json()
    assert any("deploy key" in h["text"] for h in alpha_recall["hits"])


def test_database_tool_cannot_see_other_tenant_messages(two_orgs):
    client, alpha, beta = two_orgs
    conv = _make_conversation(client, alpha)
    _chat(client, alpha, conv, "the codename is orchid")

    hits = client.post(
        "/api/v1/tools/database/invoke",
        json={"params": {"action": "search_messages", "query": "orchid"}},
        headers=beta,
    ).json()["result"]["matches"]
    assert hits == []

    own = client.post(
        "/api/v1/tools/database/invoke",
        json={"params": {"action": "search_messages", "query": "orchid"}},
        headers=alpha,
    ).json()["result"]["matches"]
    assert any("orchid" in m["content"] for m in own)


def test_analytics_counts_only_the_callers_tenant(two_orgs):
    client, alpha, beta = two_orgs
    conv = _make_conversation(client, alpha)
    _chat(client, alpha, conv, "2 + 2")

    beta_usage = client.get("/api/v1/analytics/usage", headers=beta).json()
    assert beta_usage["conversations"] == 0
    assert beta_usage["messages"] == 0
    assert beta_usage["executions"] == 0

    alpha_usage = client.get("/api/v1/analytics/usage", headers=alpha).json()
    assert alpha_usage["messages"] >= 2


def test_teammates_must_belong_to_the_same_org(two_orgs):
    client, alpha, beta = two_orgs
    alpha_agent = _make_agent(client, alpha, name="AlphaBot")

    # Beta cannot enlist Alpha's agent as a teammate.
    resp = client.post(
        "/api/v1/agents",
        json={"name": "BetaBot", "tools": [], "teammates": [alpha_agent]},
        headers=beta,
    )
    assert resp.status_code == 400
    assert "Unknown teammate" in resp.json()["detail"]


def test_same_email_in_two_orgs_logs_into_the_right_tenant(client, register_org):
    """Emails are unique per tenant, so both accounts must remain reachable."""
    register_org("First", "shared@example.com", password="firstpass123")
    register_org("Second", "shared@example.com", password="secondpass123")

    first = client.post(
        "/api/v1/auth/login",
        json={"email": "shared@example.com", "password": "firstpass123"},
    )
    second = client.post(
        "/api/v1/auth/login",
        json={"email": "shared@example.com", "password": "secondpass123"},
    )
    assert first.status_code == 200 and second.status_code == 200

    org_one = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {first.json()['access_token']}"},
    ).json()["org"]["name"]
    org_two = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {second.json()['access_token']}"},
    ).json()["org"]["name"]
    assert {org_one, org_two} == {"First", "Second"}


def test_refresh_token_cannot_be_used_as_an_access_token(auth_client, client):
    _, headers = auth_client
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@acme.com", "password": "password123"},
    ).json()
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login['refresh_token']}"},
    )
    assert resp.status_code == 401


def test_token_signed_with_a_different_secret_is_rejected(client, auth_client):
    from jose import jwt

    forged = jwt.encode(
        {"sub": "1", "org": "1", "type": "access", "jti": "x"},
        "not-the-real-secret",
        algorithm="HS256",
    )
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert resp.status_code == 401


def test_token_whose_org_claim_does_not_match_the_user_is_rejected(two_orgs):
    """A correctly signed token still has to agree with the user's real tenant."""
    from app.core.security import create_access_token

    client, alpha, beta = two_orgs
    alpha_me = client.get("/api/v1/auth/me", headers=alpha).json()
    beta_org_id = client.get("/api/v1/auth/me", headers=beta).json()["org"]["id"]

    # Alpha's user id, Beta's org id: signed by us, but internally inconsistent.
    tampered = create_access_token(alpha_me["user"]["id"], beta_org_id)
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered}"})
    assert resp.status_code == 401


# --- visibility inside one tenant -------------------------------------------


def _add_member(client, owner_headers, email, password="password123"):
    """Create a member account in the owner's org and return its auth headers."""
    created = client.post(
        "/api/v1/users",
        json={"email": email, "password": password, "role": "member"},
        headers=owner_headers,
    )
    assert created.status_code == 201, created.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_a_member_cannot_read_another_members_run(auth_client):
    """Run traces quote the user's own words, so members only see their own."""
    client, owner = auth_client
    alice = _add_member(client, owner, "alice@acme.com")
    bob = _add_member(client, owner, "bob@acme.com")

    conv = _make_conversation(client, alice)
    _chat(client, alice, conv, "remember that alice's badge number is 7781")
    execution_id = client.get("/api/v1/executions", headers=alice).json()[0]["id"]

    assert client.get("/api/v1/executions", headers=bob).json() == []
    assert client.get(f"/api/v1/executions/{execution_id}", headers=bob).status_code == 404
    assert client.post(
        f"/api/v1/executions/{execution_id}/approve", headers=bob
    ).status_code == 404

    # Alice sees her own run, and the owner sees it too (audit view).
    assert client.get(f"/api/v1/executions/{execution_id}", headers=alice).status_code == 200
    assert client.get(f"/api/v1/executions/{execution_id}", headers=owner).status_code == 200


def test_members_do_not_see_each_others_conversations_or_memory(auth_client):
    client, owner = auth_client
    alice = _add_member(client, owner, "alice@acme.com")
    bob = _add_member(client, owner, "bob@acme.com")

    conv = _make_conversation(client, alice)
    _chat(client, alice, conv, "remember that the spare key is under the mat")

    assert client.get("/api/v1/conversations", headers=bob).json() == []
    assert client.get(f"/api/v1/conversations/{conv}/messages", headers=bob).status_code == 404
    assert client.get("/api/v1/memory/facts", headers=bob).json() == []
    assert client.get("/api/v1/memory/recall", params={"q": "spare key"}, headers=bob).json()[
        "hits"
    ] == []
    # Even the owner, who can audit runs, does not inherit another user's chats.
    assert client.get(f"/api/v1/conversations/{conv}/messages", headers=owner).status_code == 404
