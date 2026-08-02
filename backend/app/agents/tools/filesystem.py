"""File-system tool: a sandboxed per-tenant workspace on local disk.

The spec asks for a file-system integration. Giving an agent unrestricted disk
access would be reckless, so each (org, user) pair gets its own directory under
``settings.WORKSPACE_ROOT`` and every path is resolved and checked to be inside
it. Traversal attempts (``../``, absolute paths, symlink tricks) are rejected
before any I/O happens.

Actions: ``write``, ``read``, ``list``, ``delete``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agents.tools.base import Tool, ToolContext, ToolError
from app.core.config import settings

# Cap file size so a runaway agent cannot fill the disk or blow up a response.
_MAX_BYTES = 64 * 1024


def _require_ctx(ctx: ToolContext) -> None:
    if ctx.org_id is None or ctx.user_id is None:
        raise ToolError("filesystem tool requires an authenticated context")


def tenant_root(org_id: int, user_id: int) -> Path:
    """Absolute sandbox directory for one tenant user (created on demand)."""
    root = Path(settings.WORKSPACE_ROOT).expanduser().resolve()
    path = root / f"org_{org_id}" / f"user_{user_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_in_sandbox(org_id: int, user_id: int, relative: str) -> Path:
    """Resolve ``relative`` inside the tenant sandbox or raise ToolError.

    ``Path.resolve`` collapses ``..`` and follows symlinks, so comparing the
    resolved result against the resolved sandbox root is what actually makes
    the jail hold. A string check on "``..``" alone would not.
    """
    name = (relative or "").strip()
    if not name:
        raise ToolError("a 'path' is required")
    if Path(name).is_absolute() or name.startswith("~"):
        raise ToolError("path must be relative to your workspace")
    root = tenant_root(org_id, user_id)
    candidate = (root / name).resolve()
    if candidate != root and root not in candidate.parents:
        raise ToolError("path escapes the workspace sandbox")
    return candidate


def _run(params: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    _require_ctx(ctx)
    action = str(params.get("action", "list")).lower()
    root = tenant_root(ctx.org_id, ctx.user_id)

    if action == "list":
        files = sorted(
            str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()
        )
        return {"action": "list", "files": files}

    if action == "write":
        target = resolve_in_sandbox(ctx.org_id, ctx.user_id, str(params.get("path", "")))
        content = str(params.get("content", ""))
        data = content.encode("utf-8")
        if len(data) > _MAX_BYTES:
            raise ToolError(f"content exceeds the {_MAX_BYTES} byte limit")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return {
            "action": "write",
            "path": str(target.relative_to(root)),
            "bytes": len(data),
        }

    if action == "read":
        target = resolve_in_sandbox(ctx.org_id, ctx.user_id, str(params.get("path", "")))
        if not target.is_file():
            raise ToolError(f"file not found: {params.get('path')}")
        content = target.read_text(encoding="utf-8", errors="replace")[:_MAX_BYTES]
        return {"action": "read", "path": str(target.relative_to(root)), "content": content}

    if action == "delete":
        target = resolve_in_sandbox(ctx.org_id, ctx.user_id, str(params.get("path", "")))
        if not target.is_file():
            raise ToolError(f"file not found: {params.get('path')}")
        target.unlink()
        return {"action": "delete", "path": str(target.relative_to(root))}

    raise ToolError(f"Unknown action '{action}' (use write|read|list|delete)")


filesystem_tool = Tool(
    name="filesystem",
    description="Read, write, list and delete text files in your private, "
    "sandboxed workspace directory.",
    parameters={
        "action": "One of write | read | list | delete",
        "path": "Path relative to your workspace, e.g. 'notes/todo.md'",
        "content": "Text to write (for write)",
    },
    run=_run,
    examples=['{"action": "write", "path": "todo.md", "content": "ship it"}', '{"action": "list"}'],
)
