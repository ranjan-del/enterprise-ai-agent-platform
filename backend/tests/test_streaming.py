"""Server-Sent Events tests for the streaming chat endpoint."""

from __future__ import annotations

import json


def _parse_sse(text: str) -> list[dict]:
    """Split a raw SSE body into the JSON payloads it carried."""
    events = []
    for block in text.strip().split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: ") :]))
    return events


def _conversation(client, headers):
    return client.post("/api/v1/conversations", json={}, headers=headers).json()["id"]


def test_stream_emits_every_node_then_a_result(auth_client):
    client, headers = auth_client
    conv = _conversation(client, headers)

    with client.stream(
        "POST",
        f"/api/v1/conversations/{conv}/messages/stream",
        json={"content": "calculate 12 * 8"},
        headers=headers,
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        body = "".join(resp.iter_text())

    events = _parse_sse(body)
    nodes = [e["node"] for e in events if e["event"] == "step"]
    assert nodes == ["plan", "memory", "act", "reflect", "respond"]

    final = events[-1]
    assert final["event"] == "result"
    assert "96" in final["reply"]
    assert final["tools_used"] == ["calculator"]
    assert final["status"] == "completed"


def test_streamed_turn_is_persisted_exactly_once(auth_client):
    client, headers = auth_client
    conv = _conversation(client, headers)

    with client.stream(
        "POST",
        f"/api/v1/conversations/{conv}/messages/stream",
        json={"content": "hello"},
        headers=headers,
    ) as resp:
        "".join(resp.iter_text())

    messages = client.get(f"/api/v1/conversations/{conv}/messages", headers=headers).json()
    assert [m["role"] for m in messages] == ["user", "assistant"]

    executions = client.get("/api/v1/executions", headers=headers).json()
    assert len(executions) == 1


def test_stream_requires_authentication(client, auth_client):
    _, headers = auth_client
    conv = _conversation(client, headers)
    resp = client.post(
        f"/api/v1/conversations/{conv}/messages/stream", json={"content": "hi"}
    )
    assert resp.status_code == 401
