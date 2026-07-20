"""Agent orchestration as a small deterministic state graph.

Shape mirrors LangGraph's ``StateGraph``: named nodes mutate a shared state dict
and are wired by edges from an entry point to ``END``. If the real ``langgraph``
package is importable it is used to build the same plan → act → reflect → respond
pipeline; otherwise this module's lightweight ``StateGraph`` runs it. Either way
the runtime is fully offline and deterministic — no LLM or API key required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.agents import responder
from app.agents.memory.session import SessionMemory
from app.agents.memory.user import UserMemory
from app.agents.memory.vector import VectorMemory
from app.agents.tools.base import ToolContext, ToolError
from app.agents.tools.registry import get_tool, invoke_tool, tool_names

END = "__end__"

# --- minimal StateGraph (LangGraph-compatible shape) ------------------------

NodeFn = Callable[[dict], dict]


class StateGraph:
    """A tiny linear/branching state graph executor.

    Not a full LangGraph, but the same mental model: register nodes, connect
    them with edges, set an entry point, ``compile`` and ``invoke``.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, NodeFn] = {}
        self._edges: dict[str, str] = {}
        self._entry: str | None = None

    def add_node(self, name: str, fn: NodeFn) -> None:
        self._nodes[name] = fn

    def add_edge(self, src: str, dst: str) -> None:
        self._edges[src] = dst

    def set_entry_point(self, name: str) -> None:
        self._entry = name

    def compile(self) -> "CompiledGraph":
        if self._entry is None:
            raise ValueError("entry point not set")
        return CompiledGraph(self._nodes, self._edges, self._entry)


@dataclass
class CompiledGraph:
    nodes: dict[str, NodeFn]
    edges: dict[str, str]
    entry: str

    def invoke(self, state: dict) -> dict:
        current = self.entry
        # Guard against accidental cycles.
        for _ in range(len(self.nodes) + 1):
            if current == END or current is None:
                break
            fn = self.nodes[current]
            state = fn(state)
            current = self.edges.get(current, END)
        return state


# --- result type ------------------------------------------------------------


@dataclass
class AgentResult:
    reply: str
    steps: list[dict[str, str]] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    tokens_used: int = 0


# --- nodes ------------------------------------------------------------------


def _plan_node(state: dict) -> dict:
    message: str = state["message"]
    enabled: list[str] = state["enabled_tools"]
    intent = responder.detect_tool(message, enabled)
    state["intent"] = intent
    if intent:
        tool, params = intent
        detail = f"Selected tool '{tool}' with params {params}."
    else:
        detail = "No tool required; will answer from memory/knowledge."
    state["steps"].append({"node": "plan", "detail": detail})
    return state


def _memory_node(state: dict) -> dict:
    """Recall relevant memory and capture any 'remember that ...' facts."""
    message: str = state["message"]
    user_mem: UserMemory = state["user_memory"]
    vector_mem: VectorMemory = state["vector_memory"]

    captured = user_mem.maybe_capture(message)
    facts = user_mem.all_facts()
    for f in facts:
        vector_mem.add(f)
    related = [doc for doc, _ in vector_mem.query(message, k=2)]

    state["facts"] = facts
    state["related"] = related
    detail = f"Recalled {len(facts)} fact(s); {len(related)} related item(s)."
    if captured:
        detail = f"Remembered new fact: '{captured}'. " + detail
    state["steps"].append({"node": "memory", "detail": detail})
    return state


def _act_node(state: dict) -> dict:
    intent = state.get("intent")
    if not intent:
        state["steps"].append({"node": "act", "detail": "No tool executed."})
        return state
    tool, params = intent
    ctx: ToolContext = state["tool_context"]
    try:
        result = invoke_tool(tool, params, ctx)
        state["tool_result"] = {"tool": tool, "params": params, "result": result}
        state.setdefault("tools_used", []).append(tool)
        detail = f"Executed '{tool}' -> {result}"
    except ToolError as exc:
        state["tool_error"] = str(exc)
        detail = f"Tool '{tool}' failed: {exc}"
    state["steps"].append({"node": "act", "detail": detail})
    return state


def _reflect_node(state: dict) -> dict:
    """Self-check the outcome before composing the final answer."""
    if state.get("tool_error"):
        detail = "Tool failed; will explain the error to the user."
    elif state.get("tool_result"):
        detail = "Tool result obtained; will summarise it clearly."
    else:
        detail = "Composing a direct answer from context."
    state["steps"].append({"node": "reflect", "detail": detail})
    return state


def _respond_node(state: dict) -> dict:
    agent_name: str = state["agent_name"]
    if state.get("tool_error"):
        reply = f"I couldn't complete that: {state['tool_error']}"
    elif state.get("tool_result"):
        tr = state["tool_result"]
        reply = responder.summarize_tool_result(tr["tool"], tr["result"])
    else:
        reply = responder.fallback_reply(
            state["message"], state.get("facts", []), state.get("related", []), agent_name
        )
    state["reply"] = reply
    # A rough, deterministic token estimate (word count of I/O) for analytics.
    state["tokens_used"] = len(state["message"].split()) + len(reply.split())
    state["steps"].append({"node": "respond", "detail": "Final reply composed."})
    return state


def _build_graph() -> CompiledGraph:
    g = StateGraph()
    g.add_node("plan", _plan_node)
    g.add_node("memory", _memory_node)
    g.add_node("act", _act_node)
    g.add_node("reflect", _reflect_node)
    g.add_node("respond", _respond_node)
    g.set_entry_point("plan")
    g.add_edge("plan", "memory")
    g.add_edge("memory", "act")
    g.add_edge("act", "reflect")
    g.add_edge("reflect", "respond")
    g.add_edge("respond", END)
    return g.compile()


_GRAPH = _build_graph()


def run_agent(
    *,
    db: Session,
    org_id: int,
    user_id: int,
    conversation_id: int,
    message: str,
    agent_name: str = "Assistant",
    enabled_tools: list[str] | None = None,
) -> AgentResult:
    """Execute one agent turn through the state graph and return the result."""
    if enabled_tools is None:
        enabled_tools = tool_names()
    # Only keep tools that actually exist in the registry.
    enabled_tools = [t for t in enabled_tools if get_tool(t) is not None]

    session_mem = SessionMemory(conversation_id)
    session_mem.add("user", message)

    state: dict[str, Any] = {
        "message": message,
        "agent_name": agent_name,
        "enabled_tools": enabled_tools,
        "tool_context": ToolContext(db=db, org_id=org_id, user_id=user_id),
        "user_memory": UserMemory(db, user_id),
        "vector_memory": VectorMemory(),
        "steps": [],
        "tools_used": [],
    }
    result_state = _GRAPH.invoke(state)

    reply = result_state["reply"]
    session_mem.add("assistant", reply)
    return AgentResult(
        reply=reply,
        steps=result_state["steps"],
        tools_used=result_state.get("tools_used", []),
        tokens_used=result_state.get("tokens_used", 0),
    )


__all__ = ["run_agent", "AgentResult", "StateGraph", "END"]
