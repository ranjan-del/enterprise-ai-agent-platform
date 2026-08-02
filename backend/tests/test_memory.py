"""Memory layer tests: session, persistent, user and vector.

The vector scorer is exercised directly (pure function, no database) and then
through the API so the durable path is covered too.
"""

from __future__ import annotations

from app.agents.memory.vector import VectorMemory


def _conversation(client, headers):
    resp = client.post("/api/v1/conversations", json={}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _chat(client, headers, conv, content):
    resp = client.post(
        f"/api/v1/conversations/{conv}/messages", json={"content": content}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_vector_scoring_prefers_the_closer_document():
    mem = VectorMemory()
    mem.add("the deployment pipeline runs on friday")
    mem.add("lunch is at noon")
    hits = mem.query("when does the deployment run", k=2)
    assert hits, "expected at least one hit"
    assert "deployment" in hits[0][0]


def test_vector_ignores_stopword_only_overlap():
    mem = VectorMemory()
    mem.add("the and of it")
    assert mem.query("the and of it") == []


def test_user_memory_captured_and_listed(auth_client):
    client, headers = auth_client
    conv = _conversation(client, headers)
    body = _chat(client, headers, conv, "remember that my project is Apollo")
    assert "Apollo" in body["assistant_message"]["content"]

    facts = client.get("/api/v1/memory/facts", headers=headers).json()
    assert [f["fact"] for f in facts] == ["my project is Apollo"]


def test_user_memory_forget_removes_one_fact(auth_client):
    client, headers = auth_client
    conv = _conversation(client, headers)
    _chat(client, headers, conv, "remember that my project is Apollo")
    _chat(client, headers, conv, "remember that my desk is 4B")

    _chat(client, headers, conv, "forget that my project is Apollo")
    facts = [f["fact"] for f in client.get("/api/v1/memory/facts", headers=headers).json()]
    assert facts == ["my desk is 4B"]


def test_facts_can_be_added_and_deleted_through_the_api(auth_client):
    client, headers = auth_client
    created = client.post(
        "/api/v1/memory/facts", json={"fact": "the office wifi is guest-net"}, headers=headers
    )
    assert created.status_code == 201, created.text
    fact_id = created.json()["id"]

    # A manually added fact is indexed for recall as well.
    hits = client.get("/api/v1/memory/recall", params={"q": "wifi"}, headers=headers).json()["hits"]
    assert any("wifi" in h["text"] for h in hits)

    assert client.delete(f"/api/v1/memory/facts/{fact_id}", headers=headers).status_code == 204
    assert client.get("/api/v1/memory/facts", headers=headers).json() == []
    assert client.delete(f"/api/v1/memory/facts/{fact_id}", headers=headers).status_code == 404


def test_vector_recall_survives_across_conversations(auth_client):
    client, headers = auth_client
    first = _conversation(client, headers)
    _chat(client, headers, first, "the quarterly audit is scheduled for March")

    second = _conversation(client, headers)
    body = _chat(client, headers, second, "when is the quarterly audit")
    reply = body["assistant_message"]["content"]
    assert "March" in reply, reply


def test_session_window_holds_the_recent_turns(auth_client):
    client, headers = auth_client
    conv = _conversation(client, headers)
    _chat(client, headers, conv, "hello there")
    _chat(client, headers, conv, "2 + 2")

    window = client.get(f"/api/v1/memory/session/{conv}", headers=headers).json()
    roles = [t["role"] for t in window["turns"]]
    assert roles == ["user", "assistant", "user", "assistant"]
    assert window["turns"][0]["content"] == "hello there"


def test_recap_answers_from_session_memory(auth_client):
    client, headers = auth_client
    conv = _conversation(client, headers)
    _chat(client, headers, conv, "we are migrating the billing service")
    body = _chat(client, headers, conv, "recap")
    reply = body["assistant_message"]["content"]
    assert "billing service" in reply
    assert body["tools_used"] == []


def test_memory_overview_counts_every_layer(auth_client):
    client, headers = auth_client
    conv = _conversation(client, headers)
    _chat(client, headers, conv, "remember that the retro is on Thursday")

    overview = client.get("/api/v1/memory/overview", headers=headers).json()
    assert overview["facts"] == 1
    assert overview["messages"] == 2       # one user + one assistant
    assert overview["documents"] >= 2      # the fact, the message, the reply


def test_persistent_history_backs_the_session_cache(auth_client):
    """Clearing the cache must not lose the conversation: the DB is the truth."""
    from app.agents.memory.session import SessionMemory

    client, headers = auth_client
    conv = _conversation(client, headers)
    _chat(client, headers, conv, "the launch is on Tuesday")

    org_id = client.get("/api/v1/auth/me", headers=headers).json()["org"]["id"]
    SessionMemory(org_id, conv).clear()
    body = _chat(client, headers, conv, "recap")
    assert "launch is on Tuesday" in body["assistant_message"]["content"]
