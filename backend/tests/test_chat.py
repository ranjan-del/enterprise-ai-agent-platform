"""Chat + agent orchestration tests (fully offline, deterministic responder)."""

from __future__ import annotations


def _new_conversation(client, headers):
    resp = client.post("/api/v1/conversations", json={}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_chat_calculation(auth_client):
    client, headers = auth_client
    conv = _new_conversation(client, headers)
    resp = client.post(
        f"/api/v1/conversations/{conv}/messages",
        json={"content": "calculate 12 * 8"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "96" in body["assistant_message"]["content"]
    assert "calculator" in body["tools_used"]
    assert any(s["node"] == "respond" for s in body["steps"])


def test_chat_greeting_no_tool(auth_client):
    client, headers = auth_client
    conv = _new_conversation(client, headers)
    resp = client.post(
        f"/api/v1/conversations/{conv}/messages",
        json={"content": "hello"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tools_used"] == []
    assert body["assistant_message"]["content"]  # non-empty real reply


def test_chat_memory_and_notes(auth_client):
    client, headers = auth_client
    conv = _new_conversation(client, headers)

    # Remember a fact.
    client.post(
        f"/api/v1/conversations/{conv}/messages",
        json={"content": "remember that my favourite colour is teal"},
        headers=headers,
    )
    # Create a note via natural language.
    note_resp = client.post(
        f"/api/v1/conversations/{conv}/messages",
        json={"content": "note: buy milk"},
        headers=headers,
    ).json()
    assert "notes" in note_resp["tools_used"]

    # Messages persist.
    msgs = client.get(f"/api/v1/conversations/{conv}/messages", headers=headers).json()
    assert len(msgs) >= 4  # 2 user + 2 assistant


def test_agent_run_and_executions(auth_client):
    client, headers = auth_client
    agent = client.post(
        "/api/v1/agents",
        json={"name": "Mathy", "tools": ["calculator", "time"]},
        headers=headers,
    )
    assert agent.status_code == 201, agent.text
    agent_id = agent.json()["id"]

    run = client.post(
        f"/api/v1/agents/{agent_id}/run",
        json={"message": "what is 100 / 4"},
        headers=headers,
    )
    assert run.status_code == 200, run.text
    assert "25" in run.json()["reply"]

    execs = client.get(f"/api/v1/agents/{agent_id}/executions", headers=headers).json()
    assert len(execs) == 1
    assert execs[0]["status"] == "completed"


def test_analytics_usage(auth_client):
    client, headers = auth_client
    conv = _new_conversation(client, headers)
    client.post(
        f"/api/v1/conversations/{conv}/messages",
        json={"content": "2 + 2"},
        headers=headers,
    )
    usage = client.get("/api/v1/analytics/usage", headers=headers).json()
    assert usage["conversations"] >= 1
    assert usage["messages"] >= 2
    assert usage["executions"] >= 1
