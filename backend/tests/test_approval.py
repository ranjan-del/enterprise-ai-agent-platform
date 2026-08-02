"""Human-in-the-loop approval tests: pause, approve, reject."""

from __future__ import annotations


def _approval_agent(client, headers, tools=("calculator",)):
    resp = client.post(
        "/api/v1/agents",
        json={"name": "Careful", "tools": list(tools), "requires_approval": True},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_tool_call_pauses_for_approval(auth_client):
    client, headers = auth_client
    agent_id = _approval_agent(client, headers)

    run = client.post(
        f"/api/v1/agents/{agent_id}/run", json={"message": "calculate 6 * 7"}, headers=headers
    ).json()

    assert run["status"] == "awaiting_approval"
    assert run["tools_used"] == []
    assert "approval" in run["reply"].lower()

    detail = client.get(f"/api/v1/executions/{run['execution_id']}", headers=headers).json()
    assert detail["status"] == "awaiting_approval"
    assert detail["pending_action"]["tool"] == "calculator"
    assert detail["pending_action"]["params"] == {"expression": "6 * 7"}


def test_approving_replays_the_tool_and_answers(auth_client):
    client, headers = auth_client
    agent_id = _approval_agent(client, headers)
    run = client.post(
        f"/api/v1/agents/{agent_id}/run", json={"message": "calculate 6 * 7"}, headers=headers
    ).json()

    approved = client.post(
        f"/api/v1/executions/{run['execution_id']}/approve", headers=headers
    )
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["status"] == "completed"
    assert body["pending_action"] is None
    assert any("Replaying approved tool" in s["detail"] for s in body["steps"])

    messages = client.get(
        f"/api/v1/conversations/{run['conversation_id']}/messages", headers=headers
    ).json()
    assert "42" in messages[-1]["content"]


def test_rejecting_runs_nothing_and_says_so(auth_client):
    client, headers = auth_client
    agent_id = _approval_agent(client, headers, tools=["filesystem"])
    run = client.post(
        f"/api/v1/agents/{agent_id}/run",
        json={"message": "write file secrets.txt: do not do this"},
        headers=headers,
    ).json()
    assert run["status"] == "awaiting_approval"

    rejected = client.post(
        f"/api/v1/executions/{run['execution_id']}/reject", headers=headers
    ).json()
    assert rejected["status"] == "rejected"

    # The file was never written.
    files = client.post(
        "/api/v1/tools/filesystem/invoke", json={"params": {"action": "list"}}, headers=headers
    ).json()["result"]["files"]
    assert files == []

    messages = client.get(
        f"/api/v1/conversations/{run['conversation_id']}/messages", headers=headers
    ).json()
    assert "will not run" in messages[-1]["content"]


def test_deciding_twice_conflicts(auth_client):
    client, headers = auth_client
    agent_id = _approval_agent(client, headers)
    run = client.post(
        f"/api/v1/agents/{agent_id}/run", json={"message": "calculate 1 + 1"}, headers=headers
    ).json()

    assert client.post(
        f"/api/v1/executions/{run['execution_id']}/approve", headers=headers
    ).status_code == 200
    second = client.post(f"/api/v1/executions/{run['execution_id']}/approve", headers=headers)
    assert second.status_code == 409


def test_answers_without_tools_are_never_gated(auth_client):
    client, headers = auth_client
    agent_id = _approval_agent(client, headers)
    run = client.post(
        f"/api/v1/agents/{agent_id}/run", json={"message": "hello"}, headers=headers
    ).json()
    assert run["status"] == "completed"


def test_analytics_reports_awaiting_and_rejected_runs(auth_client):
    client, headers = auth_client
    agent_id = _approval_agent(client, headers)
    first = client.post(
        f"/api/v1/agents/{agent_id}/run", json={"message": "calculate 2 + 2"}, headers=headers
    ).json()
    client.post(
        f"/api/v1/agents/{agent_id}/run", json={"message": "calculate 3 + 3"}, headers=headers
    )
    client.post(f"/api/v1/executions/{first['execution_id']}/reject", headers=headers)

    stats = client.get("/api/v1/analytics/executions", headers=headers).json()
    assert stats["rejected"] == 1
    assert stats["awaiting_approval"] == 1
