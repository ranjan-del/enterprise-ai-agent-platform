"""Deterministic, offline responder logic used by the agent graph.

No LLM or API key is involved. Given a user message plus context (enabled tools,
recalled memory), these helpers decide which tool to call and craft a real,
useful assistant reply. The behaviour is deterministic, so it is fully testable.
"""

from __future__ import annotations

import re
from typing import Any

# --- intent detection -------------------------------------------------------

_CALC_RE = re.compile(
    r"(?:calculat\w*|comput\w*|what\s+is|evaluate|solve)?\s*"
    r"([-+*/%^().\d\s]*\d[-+*/%^().\d\s]*)$",
    re.IGNORECASE,
)
_MATH_CHARS_RE = re.compile(r"^[\s\d+\-*/%^().]+$")
_TIME_RE = re.compile(r"\b(what(?:'s| is)? the )?(time|date|day)\b", re.IGNORECASE)
_ECHO_RE = re.compile(r"^\s*echo\s+(.+)$", re.IGNORECASE)


def detect_tool(message: str, enabled: list[str]) -> tuple[str, dict[str, Any]] | None:
    """Return (tool_name, params) if the message maps to an enabled tool."""
    text = message.strip()

    # echo: explicit "echo ..." prefix.
    if "echo" in enabled:
        m = _ECHO_RE.match(text)
        if m:
            return "echo", {"text": m.group(1).strip()}

    # notes: "note: ...", "add a note ...", "list notes".
    if "notes" in enabled:
        low = text.lower()
        if low in ("list notes", "show notes", "my notes"):
            return "notes", {"action": "list"}
        m = re.match(r"^(?:add a |create a |new )?note[:\s]+(.+)$", text, re.IGNORECASE)
        if m:
            body = m.group(1).strip()
            title = body.split("\n", 1)[0][:60]
            return "notes", {"action": "create", "title": title, "body": body}

    # calculator: a pure math expression, or "calculate <expr>".
    if "calculator" in enabled:
        expr = _extract_expression(text)
        if expr:
            return "calculator", {"expression": expr}

    # time / date.
    if "time" in enabled and _TIME_RE.search(text):
        return "time", {}

    return None


def _extract_expression(text: str) -> str | None:
    """Pull an arithmetic expression out of the message, if present."""
    stripped = text.rstrip("?. ").strip()
    if _MATH_CHARS_RE.match(stripped) and any(c.isdigit() for c in stripped):
        # Must contain an operator to count as a calculation, not just a number.
        if any(op in stripped for op in "+-*/%^"):
            return stripped
    m = re.search(
        r"(?:calculat\w*|comput\w*|evaluate|what\s+is|solve)\s+([-+*/%^().\d\s]+)",
        text,
        re.IGNORECASE,
    )
    if m:
        candidate = m.group(1).strip().rstrip("?. ")
        if candidate and any(c.isdigit() for c in candidate):
            return candidate
    return None


# --- reply generation -------------------------------------------------------


def summarize_tool_result(tool: str, result: dict[str, Any]) -> str:
    """Turn a raw tool result into a natural-language sentence."""
    if tool == "calculator":
        return f"The result of `{result.get('expression')}` is **{result.get('result')}**."
    if tool == "time":
        return f"It is currently {result.get('time')} on {result.get('date')}."
    if tool == "echo":
        return f"Echo: {result.get('echo')}"
    if tool == "notes":
        action = result.get("action")
        if action == "create":
            note = result.get("note", {})
            return f"Saved note #{note.get('id')}: “{note.get('title')}”."
        if action == "list":
            notes = result.get("notes", [])
            if not notes:
                return "You have no notes yet."
            lines = "\n".join(f"- #{n['id']} {n['title']}" for n in notes)
            return f"You have {len(notes)} note(s):\n{lines}"
        if action == "get":
            note = result.get("note", {})
            return f"Note #{note.get('id')} — {note.get('title')}:\n{note.get('body')}"
        if action == "delete":
            return f"Deleted note #{result.get('deleted_id')}."
    return f"{tool} returned: {result}"


def fallback_reply(
    message: str,
    facts: list[str],
    related: list[str],
    agent_name: str,
) -> str:
    """Craft a helpful reply when no tool matches (pure offline heuristics)."""
    text = message.strip()
    low = text.lower()

    if any(g in low for g in ("hello", "hi ", "hey", "good morning", "good afternoon")) or low in (
        "hi",
        "hey",
        "hello",
    ):
        greeting = f"Hello! I'm {agent_name}, your workspace assistant."
        if facts:
            greeting += f" I remember that {facts[-1]}."
        return greeting + " How can I help you today?"

    if "help" in low or low.endswith("?") and "you" in low and "do" in low:
        return (
            f"I'm {agent_name}. I can do math (try 'calculate 12 * 8'), tell the time, "
            "keep notes ('note: buy milk', 'list notes'), echo text, and remember facts "
            "('remember that my project is Apollo')."
        )

    parts: list[str] = []
    if related:
        parts.append("Here's what I recall that seems related:")
        parts.extend(f"• {r}" for r in related)
    if facts and not related:
        parts.append(f"Noted. For context, I also remember: {facts[-1]}.")

    summary = _reflective_ack(text)
    parts.append(summary)
    return "\n".join(parts)


def _reflective_ack(text: str) -> str:
    """A concise acknowledgement that reflects the user's message back."""
    snippet = text if len(text) <= 140 else text[:137] + "..."
    return (
        f"You said: “{snippet}”. I've recorded this in the conversation. "
        "Ask me to calculate something, check the time, or manage notes and I'll act on it."
    )
