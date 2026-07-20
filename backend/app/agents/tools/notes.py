"""Notes tool — tenant-scoped CRUD persisted in the database (offline).

Actions: ``create``, ``list``, ``get``, ``delete``. Every note is scoped to the
calling user's org + user id via the ToolContext, so tenants never see each
other's notes.
"""

from __future__ import annotations

from typing import Any

from app.agents.tools.base import Tool, ToolContext, ToolError
from app.models.note import Note


def _require_ctx(ctx: ToolContext) -> None:
    if ctx.db is None or ctx.org_id is None or ctx.user_id is None:
        raise ToolError("notes tool requires an authenticated database context")


def _serialize(note: Note) -> dict[str, Any]:
    return {
        "id": note.id,
        "title": note.title,
        "body": note.body,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }


def _run(params: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    _require_ctx(ctx)
    action = str(params.get("action", "list")).lower()
    db = ctx.db

    if action == "create":
        title = str(params.get("title", "")).strip()
        if not title:
            raise ToolError("create requires a 'title'")
        note = Note(
            org_id=ctx.org_id,
            user_id=ctx.user_id,
            title=title,
            body=str(params.get("body", "")),
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        return {"action": "create", "note": _serialize(note)}

    if action == "list":
        notes = (
            db.query(Note)
            .filter(Note.org_id == ctx.org_id, Note.user_id == ctx.user_id)
            .order_by(Note.id.desc())
            .all()
        )
        return {"action": "list", "notes": [_serialize(n) for n in notes]}

    if action == "get":
        note = _lookup(db, ctx, params)
        return {"action": "get", "note": _serialize(note)}

    if action == "delete":
        note = _lookup(db, ctx, params)
        db.delete(note)
        db.commit()
        return {"action": "delete", "deleted_id": params.get("id")}

    raise ToolError(f"Unknown action '{action}' (use create|list|get|delete)")


def _lookup(db, ctx: ToolContext, params: dict[str, Any]) -> Note:
    note_id = params.get("id")
    if note_id is None:
        raise ToolError("this action requires a note 'id'")
    note = (
        db.query(Note)
        .filter(Note.id == int(note_id), Note.org_id == ctx.org_id, Note.user_id == ctx.user_id)
        .first()
    )
    if note is None:
        raise ToolError(f"note {note_id} not found")
    return note


notes_tool = Tool(
    name="notes",
    description="Create, list, read, and delete personal notes (persisted, tenant-scoped).",
    parameters={
        "action": "One of create | list | get | delete",
        "title": "Note title (for create)",
        "body": "Note body (for create)",
        "id": "Note id (for get / delete)",
    },
    run=_run,
    examples=['{"action": "create", "title": "Ideas", "body": "Ship it"}', '{"action": "list"}'],
)
