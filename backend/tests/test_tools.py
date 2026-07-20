"""Tool tests: calculator safety + correctness, notes CRUD, utility tools."""

from __future__ import annotations

import pytest

from app.agents.tools.base import ToolError
from app.agents.tools.calculator import safe_eval


def test_calculator_basic():
    assert safe_eval("2 + 3 * 4") == 14
    assert safe_eval("(10 - 4) / 2") == 3
    assert safe_eval("2 ** 10") == 1024


def test_calculator_functions():
    assert safe_eval("sqrt(144)") == 12


@pytest.mark.parametrize("expr", ["__import__('os')", "1 + foo", "open('x')", ""])
def test_calculator_rejects_unsafe(expr):
    with pytest.raises(ToolError):
        safe_eval(expr)


def test_calculator_via_api(auth_client):
    client, headers = auth_client
    resp = client.post(
        "/api/v1/tools/calculator/invoke",
        json={"params": {"expression": "6 * 7"}},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["result"]["result"] == 42


def test_notes_crud_via_api(auth_client):
    client, headers = auth_client
    created = client.post(
        "/api/v1/tools/notes/invoke",
        json={"params": {"action": "create", "title": "Groceries", "body": "milk, eggs"}},
        headers=headers,
    )
    assert created.status_code == 200, created.text
    note_id = created.json()["result"]["note"]["id"]

    listed = client.post(
        "/api/v1/tools/notes/invoke",
        json={"params": {"action": "list"}},
        headers=headers,
    ).json()["result"]["notes"]
    assert any(n["id"] == note_id for n in listed)

    deleted = client.post(
        "/api/v1/tools/notes/invoke",
        json={"params": {"action": "delete", "id": note_id}},
        headers=headers,
    )
    assert deleted.status_code == 200


def test_list_tools_requires_auth(client):
    assert client.get("/api/v1/tools").status_code == 401


def test_tool_error_returns_400(auth_client):
    client, headers = auth_client
    resp = client.post(
        "/api/v1/tools/calculator/invoke",
        json={"params": {"expression": "1 +"}},
        headers=headers,
    )
    assert resp.status_code == 400
