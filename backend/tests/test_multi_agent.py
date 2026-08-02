"""Multi-agent collaboration tests: delegation to a teammate agent."""

from __future__ import annotations


def _agent(client, headers, name, tools, teammates=None):
    resp = client.post(
        "/api/v1/agents",
        json={"name": name, "tools": tools, "teammates": teammates or []},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_agent_delegates_a_tool_it_does_not_have(auth_client):
    client, headers = auth_client
    specialist = _agent(client, headers, "Mathy", ["calculator"])
    coordinator = _agent(client, headers, "Coordinator", ["notes"], teammates=[specialist])

    run = client.post(
        f"/api/v1/agents/{coordinator}/run", json={"message": "calculate 9 * 9"}, headers=headers
    ).json()

    assert "81" in run["reply"]
    assert "handled by Mathy" in run["reply"]
    assert run["tools_used"] == ["calculator"]
    plan = next(s for s in run["steps"] if s["node"] == "plan")
    assert "delegating" in plan["detail"]
    act = next(s for s in run["steps"] if s["node"] == "act")
    assert act["detail"].startswith("[via Mathy]")


def test_own_tools_win_over_a_teammates(auth_client):
    client, headers = auth_client
    specialist = _agent(client, headers, "Mathy", ["calculator"])
    generalist = _agent(client, headers, "Generalist", ["calculator"], teammates=[specialist])

    run = client.post(
        f"/api/v1/agents/{generalist}/run", json={"message": "calculate 5 + 5"}, headers=headers
    ).json()
    assert "handled by" not in run["reply"]
    assert "10" in run["reply"]


def test_delegated_tool_usage_shows_up_in_analytics(auth_client):
    client, headers = auth_client
    specialist = _agent(client, headers, "Mathy", ["calculator"])
    coordinator = _agent(client, headers, "Coordinator", [], teammates=[specialist])

    client.post(
        f"/api/v1/agents/{coordinator}/run", json={"message": "calculate 4 * 4"}, headers=headers
    )
    stats = client.get("/api/v1/analytics/executions", headers=headers).json()
    assert stats["tool_usage"].get("calculator") == 1


def test_an_agent_cannot_be_its_own_teammate(auth_client):
    client, headers = auth_client
    agent_id = _agent(client, headers, "Solo", ["calculator"])
    resp = client.patch(
        f"/api/v1/agents/{agent_id}", json={"teammates": [agent_id]}, headers=headers
    )
    assert resp.status_code == 400


def test_teammates_round_trip_through_the_api(auth_client):
    client, headers = auth_client
    specialist = _agent(client, headers, "Mathy", ["calculator"])
    coordinator = _agent(client, headers, "Coordinator", [], teammates=[specialist])

    fetched = client.get(f"/api/v1/agents/{coordinator}", headers=headers).json()
    assert fetched["teammates"] == [specialist]
    assert fetched["requires_approval"] is False
