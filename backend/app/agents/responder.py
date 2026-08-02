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
_WEATHER_RE = re.compile(r"\bweather\b(?:\s+(?:in|for|at))?\s+(.+)$", re.IGNORECASE)
_GITHUB_RE = re.compile(
    r"\bgithub\b(?:\s+(?:repo|repository))?\s+([\w.-]+/[\w.-]+)", re.IGNORECASE
)
_STATS_RE = re.compile(
    r"\b(workspace stats|my stats|how many (?:conversations|messages|agents|users|executions))\b",
    re.IGNORECASE,
)
_SEARCH_MSG_RE = re.compile(
    r"\bsearch (?:my )?(?:messages|conversations|history) for\s+(.+)$", re.IGNORECASE
)
_LIST_CONVS_RE = re.compile(r"\b(list|show) (?:my )?conversations\b", re.IGNORECASE)
_LIST_FILES_RE = re.compile(r"\b(list|show) (?:my )?files\b", re.IGNORECASE)
_READ_FILE_RE = re.compile(r"\b(?:read|open|show|cat) file\s+(\S+)", re.IGNORECASE)
_DELETE_FILE_RE = re.compile(r"\b(?:delete|remove) file\s+(\S+)", re.IGNORECASE)
_WRITE_FILE_RE = re.compile(
    r"\b(?:write|save|create) file\s+(\S+?)\s*(?::|\bwith\b|\bcontaining\b)\s*(.+)$",
    re.IGNORECASE | re.DOTALL,
)
# "recap", "what did we talk about", "summarise this conversation".
_RECAP_RE = re.compile(
    r"\b(recap|summar(?:ise|ize)(?: this)?(?: conversation| chat)?|"
    r"what (?:did|have) we (?:talk|talked|discuss|discussed)|what did i (?:just )?say)\b",
    re.IGNORECASE,
)


def detect_tool(message: str, enabled: list[str]) -> tuple[str, dict[str, Any]] | None:
    """Return (tool_name, params) if the message maps to an enabled tool.

    Order matters: the most specific patterns are checked first so that, for
    example, "list files" never falls through to the notes tool. Detection is
    pure string matching, which is why the whole runtime stays deterministic
    and needs no model.
    """
    text = message.strip()

    # echo: explicit "echo ..." prefix.
    if "echo" in enabled:
        m = _ECHO_RE.match(text)
        if m:
            return "echo", {"text": m.group(1).strip()}

    # filesystem: file verbs are explicit, so they are matched before notes.
    if "filesystem" in enabled:
        if _LIST_FILES_RE.search(text):
            return "filesystem", {"action": "list"}
        m = _WRITE_FILE_RE.search(text)
        if m:
            return "filesystem", {
                "action": "write",
                "path": m.group(1).strip(),
                "content": m.group(2).strip(),
            }
        m = _READ_FILE_RE.search(text)
        if m:
            return "filesystem", {"action": "read", "path": m.group(1).strip()}
        m = _DELETE_FILE_RE.search(text)
        if m:
            return "filesystem", {"action": "delete", "path": m.group(1).strip()}

    # database: workspace introspection in plain language.
    if "database" in enabled:
        m = _SEARCH_MSG_RE.search(text)
        if m:
            return "database", {"action": "search_messages", "query": m.group(1).strip().rstrip("?.")}
        if _LIST_CONVS_RE.search(text):
            return "database", {"action": "conversations"}
        if _STATS_RE.search(text):
            return "database", {"action": "stats"}

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

    # weather: "weather in Bengaluru".
    if "weather" in enabled:
        m = _WEATHER_RE.search(text)
        if m:
            location = m.group(1).strip().rstrip("?.").strip()
            if location:
                return "weather", {"location": location}

    # github: "github fastapi/fastapi".
    if "github" in enabled:
        m = _GITHUB_RE.search(text)
        if m:
            return "github", {"repo": m.group(1).strip()}

    # calculator: a pure math expression, or "calculate <expr>".
    if "calculator" in enabled:
        expr = _extract_expression(text)
        if expr:
            return "calculator", {"expression": expr}

    # time / date.
    if "time" in enabled and _TIME_RE.search(text):
        return "time", {}

    return None


def wants_recap(message: str) -> bool:
    """True when the user is asking about the conversation so far."""
    return bool(_RECAP_RE.search(message))


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
    if tool == "database":
        return _summarize_database(result)
    if tool == "filesystem":
        return _summarize_filesystem(result)
    if tool == "weather":
        return (
            f"{result.get('location')}: {result.get('conditions')}, "
            f"{result.get('temperature_c')}°C, wind {result.get('wind_kph')} km/h."
        )
    if tool == "github":
        return (
            f"**{result.get('repo')}**: {result.get('description') or 'no description'}\n"
            f"★ {result.get('stars')} · forks {result.get('forks')} · "
            f"open issues {result.get('open_issues')} · {result.get('language')}"
        )
    return f"{tool} returned: {result}"


def _summarize_database(result: dict[str, Any]) -> str:
    action = result.get("action")
    if action == "stats":
        s = result.get("stats", {})
        return (
            "Workspace snapshot: "
            f"{s.get('conversations')} conversation(s), {s.get('messages')} message(s), "
            f"{s.get('agents')} agent(s), {s.get('users')} user(s), "
            f"{s.get('executions')} execution(s)."
        )
    if action == "conversations":
        convs = result.get("conversations", [])
        if not convs:
            return "You have no conversations yet."
        lines = "\n".join(f"- #{c['id']} {c['title']}" for c in convs)
        return f"Your {len(convs)} most recent conversation(s):\n{lines}"
    if action == "agents":
        agents = result.get("agents", [])
        if not agents:
            return "This workspace has no agents yet."
        lines = "\n".join(f"- #{a['id']} {a['name']} ({', '.join(a['tools']) or 'no tools'})" for a in agents)
        return f"{len(agents)} agent(s) in this workspace:\n{lines}"
    if action == "search_messages":
        matches = result.get("matches", [])
        if not matches:
            return f"No messages mention “{result.get('query')}”."
        lines = "\n".join(f"- [{m['role']}] {m['content'][:90]}" for m in matches)
        return f"{len(matches)} message(s) mention “{result.get('query')}”:\n{lines}"
    return f"database returned: {result}"


def _summarize_filesystem(result: dict[str, Any]) -> str:
    action = result.get("action")
    if action == "list":
        files = result.get("files", [])
        if not files:
            return "Your workspace folder is empty."
        return f"{len(files)} file(s) in your workspace:\n" + "\n".join(f"- {f}" for f in files)
    if action == "write":
        return f"Wrote {result.get('bytes')} byte(s) to `{result.get('path')}`."
    if action == "read":
        return f"`{result.get('path')}`:\n{result.get('content')}"
    if action == "delete":
        return f"Deleted `{result.get('path')}`."
    return f"filesystem returned: {result}"


def recap_reply(recent_turns: list[dict[str, str]], agent_name: str) -> str:
    """Summarise the conversation so far from short-term (session) memory.

    ``recent_turns`` is the rolling window kept by SessionMemory. The current
    user message is already in it, so it is trimmed off before summarising.
    """
    history = [t for t in recent_turns if t.get("content")][:-1]
    if not history:
        return "This is the start of our conversation, so there is nothing to recap yet."
    lines = [f"- {t['role']}: {t['content'][:100]}" for t in history[-6:]]
    return (
        f"Here's the recap from my short-term memory ({len(history)} turn(s) so far):\n"
        + "\n".join(lines)
    )


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
            f"I'm {agent_name}. I can do math ('calculate 12 * 8'), tell the time, "
            "keep notes ('note: buy milk', 'list notes'), work with files in your "
            "sandbox ('write file todo.md: ship it', 'list files'), query your "
            "workspace ('workspace stats', 'search my messages for invoice'), recap "
            "the conversation ('recap'), and remember facts ('remember that my "
            "project is Apollo'). Weather and GitHub lookups work when network "
            "tools are enabled."
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
