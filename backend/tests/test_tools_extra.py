"""Tests for the database, filesystem and network tools.

The network tools are tested in the state the whole suite runs in: disabled.
Their pure parsers are tested against captured payload shapes, so behaviour is
verified without ever making a request.
"""

from __future__ import annotations

import pytest

from app.agents.tools.base import ToolContext, ToolError
from app.agents.tools.filesystem import resolve_in_sandbox
from app.agents.tools.network import github_tool, parse_forecast, parse_repo, weather_tool
from app.agents.tools.registry import get_tool, offline_tool_names, tool_names


# --- registry ---------------------------------------------------------------


def test_registry_exposes_every_spec_tool():
    names = set(tool_names())
    assert {"calculator", "notes", "database", "filesystem", "time", "echo", "weather", "github"} <= names


def test_offline_tool_names_excludes_network_tools():
    assert "weather" not in offline_tool_names()
    assert "github" not in offline_tool_names()
    assert "calculator" in offline_tool_names()


def test_tool_listing_flags_network_requirements(auth_client):
    client, headers = auth_client
    tools = {t["name"]: t for t in client.get("/api/v1/tools", headers=headers).json()}
    assert tools["weather"]["requires_network"] is True
    assert tools["calculator"]["requires_network"] is False


# --- database ---------------------------------------------------------------


def test_database_stats_and_search(auth_client):
    client, headers = auth_client
    conv = client.post("/api/v1/conversations", json={}, headers=headers).json()["id"]
    client.post(
        f"/api/v1/conversations/{conv}/messages",
        json={"content": "the mango harvest starts in June"},
        headers=headers,
    )

    stats = client.post(
        "/api/v1/tools/database/invoke", json={"params": {"action": "stats"}}, headers=headers
    ).json()["result"]["stats"]
    assert stats["conversations"] == 1
    assert stats["messages"] == 2
    assert stats["users"] == 1

    matches = client.post(
        "/api/v1/tools/database/invoke",
        json={"params": {"action": "search_messages", "query": "mango"}},
        headers=headers,
    ).json()["result"]["matches"]
    assert any("mango" in m["content"] for m in matches)


def test_database_rejects_unknown_action(auth_client):
    client, headers = auth_client
    resp = client.post(
        "/api/v1/tools/database/invoke",
        json={"params": {"action": "drop_tables"}},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "Unknown action" in resp.json()["detail"]


def test_database_tool_answers_in_chat(auth_client):
    client, headers = auth_client
    conv = client.post("/api/v1/conversations", json={}, headers=headers).json()["id"]
    body = client.post(
        f"/api/v1/conversations/{conv}/messages",
        json={"content": "workspace stats"},
        headers=headers,
    ).json()
    assert "database" in body["tools_used"]
    assert "Workspace snapshot" in body["assistant_message"]["content"]


# --- filesystem -------------------------------------------------------------


def test_filesystem_write_read_list_delete(auth_client):
    client, headers = auth_client

    written = client.post(
        "/api/v1/tools/filesystem/invoke",
        json={"params": {"action": "write", "path": "notes/todo.md", "content": "ship it"}},
        headers=headers,
    )
    assert written.status_code == 200, written.text
    assert written.json()["result"]["bytes"] == len("ship it")

    listed = client.post(
        "/api/v1/tools/filesystem/invoke", json={"params": {"action": "list"}}, headers=headers
    ).json()["result"]["files"]
    assert listed == ["notes/todo.md"]

    read = client.post(
        "/api/v1/tools/filesystem/invoke",
        json={"params": {"action": "read", "path": "notes/todo.md"}},
        headers=headers,
    ).json()["result"]
    assert read["content"] == "ship it"

    deleted = client.post(
        "/api/v1/tools/filesystem/invoke",
        json={"params": {"action": "delete", "path": "notes/todo.md"}},
        headers=headers,
    )
    assert deleted.status_code == 200
    assert client.post(
        "/api/v1/tools/filesystem/invoke", json={"params": {"action": "list"}}, headers=headers
    ).json()["result"]["files"] == []


@pytest.mark.parametrize(
    "path",
    ["../escape.txt", "../../etc/passwd", "/etc/passwd", "~/secrets", "notes/../../out.txt"],
)
def test_filesystem_rejects_paths_outside_the_sandbox(path):
    with pytest.raises(ToolError):
        resolve_in_sandbox(1, 1, path)


def test_filesystem_traversal_is_rejected_through_the_api(auth_client):
    client, headers = auth_client
    resp = client.post(
        "/api/v1/tools/filesystem/invoke",
        json={"params": {"action": "write", "path": "../escape.txt", "content": "nope"}},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "sandbox" in resp.json()["detail"] or "relative" in resp.json()["detail"]


def test_filesystem_tool_answers_in_chat(auth_client):
    client, headers = auth_client
    conv = client.post("/api/v1/conversations", json={}, headers=headers).json()["id"]
    body = client.post(
        f"/api/v1/conversations/{conv}/messages",
        json={"content": "write file plan.md: launch on Friday"},
        headers=headers,
    ).json()
    assert body["tools_used"] == ["filesystem"]
    assert "plan.md" in body["assistant_message"]["content"]


# --- network (disabled by default) -----------------------------------------


def test_network_tools_refuse_to_run_when_disabled():
    ctx = ToolContext(db=None, org_id=1, user_id=1)
    with pytest.raises(ToolError) as weather_err:
        weather_tool.invoke({"location": "Bengaluru"}, ctx)
    assert "ALLOW_NETWORK_TOOLS" in str(weather_err.value)

    with pytest.raises(ToolError) as github_err:
        github_tool.invoke({"repo": "fastapi/fastapi"}, ctx)
    assert "ALLOW_NETWORK_TOOLS" in str(github_err.value)


def test_disabled_network_tool_surfaces_as_a_failed_run(auth_client):
    """The agent explains the refusal instead of inventing a forecast."""
    client, headers = auth_client
    agent = client.post(
        "/api/v1/agents", json={"name": "Meteo", "tools": ["weather"]}, headers=headers
    ).json()["id"]

    run = client.post(
        f"/api/v1/agents/{agent}/run", json={"message": "weather in Bengaluru"}, headers=headers
    ).json()
    assert "internet access" in run["reply"]
    assert run["tools_used"] == []

    detail = client.get(f"/api/v1/executions/{run['execution_id']}", headers=headers).json()
    assert detail["status"] == "failed"


def test_forecast_parser_maps_weather_codes():
    payload = {
        "current": {
            "time": "2026-01-01T10:00",
            "temperature_2m": 27.4,
            "weather_code": 3,
            "wind_speed_10m": 11.2,
        }
    }
    parsed = parse_forecast("Bengaluru", payload)
    assert parsed == {
        "location": "Bengaluru",
        "temperature_c": 27.4,
        "wind_kph": 11.2,
        "conditions": "overcast",
        "observed_at": "2026-01-01T10:00",
    }


def test_forecast_parser_rejects_an_unexpected_payload():
    with pytest.raises(ToolError):
        parse_forecast("Nowhere", {"current": {}})


def test_repo_parser_extracts_the_useful_fields():
    payload = {
        "full_name": "fastapi/fastapi",
        "description": "FastAPI framework",
        "stargazers_count": 100,
        "forks_count": 20,
        "open_issues_count": 5,
        "language": "Python",
        "html_url": "https://github.com/fastapi/fastapi",
    }
    parsed = parse_repo(payload)
    assert parsed["repo"] == "fastapi/fastapi"
    assert parsed["stars"] == 100
    assert parsed["language"] == "Python"


def test_repo_parser_rejects_an_unexpected_payload():
    with pytest.raises(ToolError):
        parse_repo({"message": "Not Found"})


def test_github_tool_validates_the_repo_format(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "ALLOW_NETWORK_TOOLS", True)
    with pytest.raises(ToolError) as err:
        github_tool.invoke({"repo": "not-a-repo"}, ToolContext())
    assert "owner/name" in str(err.value)


def test_get_tool_returns_none_for_unknown_names():
    assert get_tool("definitely-not-a-tool") is None
