"""Agent orchestration as a small deterministic state graph.

The shape mirrors LangGraph's ``StateGraph``: named nodes mutate a shared state
dict and are wired by edges from an entry point to ``END``. It is implemented
here rather than pulled in as a dependency for two reasons: the pipeline is
linear enough that the executor fits in forty lines, and owning it keeps the
whole runtime importable, deterministic and offline with no LLM, no API key and
no extra package.

The pipeline is::

    plan -> memory -> act -> reflect -> respond

``plan``     picks a tool (its own, or a teammate's) from the message.
``memory``   recalls the four memory layers and captures new facts.
``act``      runs the tool, or pauses if the agent needs human approval.
``reflect``  self-checks the outcome before wording the answer.
``respond``  composes the final reply and estimates tokens.

Every node appends a ``{node, detail}`` record to the trace, which is what the
Logs UI shows, what analytics aggregates, and what the SSE endpoint streams.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.agents import responder
from app.agents.memory.persistent import PersistentMemory
from app.agents.memory.session import SessionMemory
from app.agents.memory.user import UserMemory
from app.agents.memory.vector import TenantVectorMemory
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

    def stream(self, state: dict) -> Iterator[tuple[str, dict]]:
        """Run the graph, yielding ``(node_name, state)`` after each node.

        Streaming is the primitive and ``invoke`` is built on top of it, so the
        SSE endpoint and the plain request path run exactly the same code.
        """
        current = self.entry
        # Guard against accidental cycles.
        for _ in range(len(self.nodes) + 1):
            if current == END or current is None:
                break
            fn = self.nodes[current]
            state = fn(state)
            yield current, state
            current = self.edges.get(current, END)

    def invoke(self, state: dict) -> dict:
        for _, state in self.stream(state):
            pass
        return state


# --- result types -----------------------------------------------------------

COMPLETED = "completed"
FAILED = "failed"
AWAITING_APPROVAL = "awaiting_approval"


@dataclass
class AgentResult:
    reply: str
    steps: list[dict[str, str]] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    tokens_used: int = 0
    status: str = COMPLETED
    # Set when the run paused for approval: {"tool", "params", "message"}.
    pending_action: dict[str, Any] | None = None
    # Name of the teammate agent that handled the tool call, if any.
    delegated_to: str | None = None


@dataclass
class AgentEvent:
    """One item of a streamed run: a finished node, or the final result."""

    type: str                      # "step" | "result"
    node: str = ""
    detail: str = ""
    result: AgentResult | None = None


@dataclass
class Teammate:
    """A peer agent this agent may hand a tool call to (same org, always)."""

    id: int
    name: str
    tools: list[str]


# --- nodes ------------------------------------------------------------------


def _plan_node(state: dict) -> dict:
    """Decide what to do: answer directly, call a tool, or delegate one."""
    message: str = state["message"]
    enabled: list[str] = state["enabled_tools"]

    # A resumed run replays the exact tool call the human approved instead of
    # re-deriving it, so approving can never execute something different from
    # what was shown in the approval prompt.
    forced = state.get("forced_intent")
    if forced is not None:
        tool, params = forced
        state["intent"] = (tool, params)
        state["delegate"] = None
        state["steps"].append(
            {"node": "plan", "detail": f"Replaying approved tool '{tool}' with params {params}."}
        )
        return state

    if responder.wants_recap(message):
        state["recap"] = True
        state["intent"] = None
        state["steps"].append(
            {"node": "plan", "detail": "Recap requested; will answer from session memory."}
        )
        return state

    intent = responder.detect_tool(message, enabled)
    delegate: Teammate | None = None
    if intent is None:
        # Multi-agent: if this agent cannot serve the request, look for a
        # teammate whose enabled tools can. First match wins, which keeps the
        # hand-off deterministic.
        for mate in state.get("teammates", []):
            mate_intent = responder.detect_tool(message, mate.tools)
            if mate_intent is not None:
                intent, delegate = mate_intent, mate
                break

    state["intent"] = intent
    state["delegate"] = delegate
    if intent and delegate:
        tool, params = intent
        detail = (
            f"No local tool matched; delegating '{tool}' to teammate "
            f"'{delegate.name}' with params {params}."
        )
    elif intent:
        tool, params = intent
        detail = f"Selected tool '{tool}' with params {params}."
    else:
        detail = "No tool required; will answer from memory/knowledge."
    state["steps"].append({"node": "plan", "detail": detail})
    return state


def _memory_node(state: dict) -> dict:
    """Recall all four memory layers and capture anything worth remembering."""
    message: str = state["message"]
    user_mem: UserMemory = state["user_memory"]
    vector_mem: TenantVectorMemory = state["vector_memory"]
    session_mem: SessionMemory = state["session_memory"]
    persistent_mem: PersistentMemory = state["persistent_memory"]

    captured = user_mem.maybe_capture(message)
    forgotten = None if captured else user_mem.maybe_forget(message)
    if captured:
        vector_mem.index(captured, kind="fact")

    # The user's own words are indexed so later turns can recall them. The
    # current message is filtered out of its own recall results below.
    vector_mem.index(message, kind="message", conversation_id=state.get("conversation_id"))

    facts = user_mem.all_facts()
    hits = [h for h in vector_mem.search(message, k=3) if h.text.strip() != message.strip()]
    related = [h.text for h in hits[:2]]

    session_turns = session_mem.history()
    # Session memory is a cache: if it is cold (Redis restart, new process),
    # fall back to the durable message history for the same window. The current
    # message is appended so both paths end with the turn being handled, which
    # is what the recap summariser assumes.
    if len(session_turns) <= 1:
        session_turns = [
            {"role": m.role, "content": m.content} for m in persistent_mem.recent(limit=10)
        ]
        session_turns.append({"role": "user", "content": message})

    state["facts"] = facts
    state["related"] = related
    state["captured_fact"] = captured
    state["forgotten_fact"] = forgotten
    state["session_turns"] = session_turns

    detail = (
        f"Recalled {len(facts)} fact(s), {len(related)} related item(s), "
        f"{len(session_turns)} recent turn(s)."
    )
    if captured:
        detail = f"Remembered new fact: '{captured}'. " + detail
    if forgotten:
        detail = f"Forgot fact: '{forgotten}'. " + detail
    state["steps"].append({"node": "memory", "detail": detail})
    return state


def _act_node(state: dict) -> dict:
    """Execute the planned tool, unless a human has to approve it first."""
    intent = state.get("intent")
    if not intent:
        state["steps"].append({"node": "act", "detail": "No tool executed."})
        return state

    tool, params = intent

    # Human-in-the-loop gate. The run stops here and is resumed later by
    # POST /executions/{id}/approve, which replays this exact tool + params.
    if state.get("requires_approval") and not state.get("pre_approved"):
        state["awaiting_approval"] = True
        state["pending_action"] = {"tool": tool, "params": params, "message": state["message"]}
        state["steps"].append(
            {"node": "act", "detail": f"Paused: '{tool}' needs human approval before it runs."}
        )
        return state

    ctx: ToolContext = state["tool_context"]
    try:
        result = invoke_tool(tool, params, ctx)
        state["tool_result"] = {"tool": tool, "params": params, "result": result}
        state.setdefault("tools_used", []).append(tool)
        detail = f"Executed '{tool}' -> {result}"
        delegate = state.get("delegate")
        if delegate is not None:
            detail = f"[via {delegate.name}] " + detail
    except ToolError as exc:
        state["tool_error"] = str(exc)
        detail = f"Tool '{tool}' failed: {exc}"
    state["steps"].append({"node": "act", "detail": detail})
    return state


def _reflect_node(state: dict) -> dict:
    """Self-check the outcome before composing the final answer."""
    if state.get("awaiting_approval"):
        detail = "Waiting on a human decision; will ask for approval."
    elif state.get("tool_error"):
        detail = "Tool failed; will explain the error to the user."
    elif state.get("tool_result"):
        detail = "Tool result obtained; will summarise it clearly."
    elif state.get("recap"):
        detail = "Will summarise the conversation from short-term memory."
    else:
        detail = "Composing a direct answer from context."
    state["steps"].append({"node": "reflect", "detail": detail})
    return state


def _respond_node(state: dict) -> dict:
    agent_name: str = state["agent_name"]
    delegate = state.get("delegate")

    if state.get("awaiting_approval"):
        action = state["pending_action"]
        reply = (
            f"This needs your approval first: I want to run **{action['tool']}** "
            f"with `{action['params']}`. Approve or reject it from the Logs page."
        )
    elif state.get("tool_error"):
        reply = f"I couldn't complete that: {state['tool_error']}"
    elif state.get("tool_result"):
        tr = state["tool_result"]
        reply = responder.summarize_tool_result(tr["tool"], tr["result"])
        if delegate is not None:
            reply = f"(handled by {delegate.name}) " + reply
    elif state.get("recap"):
        reply = responder.recap_reply(state.get("session_turns", []), agent_name)
    else:
        reply = responder.fallback_reply(
            state["message"], state.get("facts", []), state.get("related", []), agent_name
        )
        if state.get("captured_fact"):
            reply = f"Got it, I'll remember that {state['captured_fact']}.\n" + reply
        elif state.get("forgotten_fact"):
            reply = f"Done, I've forgotten that {state['forgotten_fact']}.\n" + reply

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


def _initial_state(
    *,
    db: Session,
    org_id: int,
    user_id: int,
    conversation_id: int,
    message: str,
    agent_name: str,
    enabled_tools: list[str] | None,
    teammates: list[Teammate] | None,
    requires_approval: bool,
    pre_approved: bool,
    forced_intent: tuple[str, dict[str, Any]] | None,
    record_user_turn: bool,
) -> dict[str, Any]:
    if enabled_tools is None:
        enabled_tools = tool_names()
    # Only keep tools that actually exist in the registry.
    enabled_tools = [t for t in enabled_tools if get_tool(t) is not None]

    session_mem = SessionMemory(org_id, conversation_id)
    # A resumed run re-uses a turn that is already in session memory.
    if record_user_turn:
        session_mem.add("user", message)

    return {
        "message": message,
        "agent_name": agent_name,
        "conversation_id": conversation_id,
        "enabled_tools": enabled_tools,
        "teammates": teammates or [],
        "requires_approval": requires_approval,
        "pre_approved": pre_approved,
        "forced_intent": forced_intent,
        "tool_context": ToolContext(db=db, org_id=org_id, user_id=user_id),
        "session_memory": session_mem,
        "persistent_memory": PersistentMemory(db, conversation_id),
        "user_memory": UserMemory(db, org_id, user_id),
        "vector_memory": TenantVectorMemory(db, org_id, user_id),
        "steps": [],
        "tools_used": [],
    }


def _status_for(state: dict) -> str:
    """A run that could not perform the requested action is recorded as failed.

    The user still gets a helpful reply, but analytics should not count a tool
    error as a clean run.
    """
    if state.get("awaiting_approval"):
        return AWAITING_APPROVAL
    if state.get("tool_error"):
        return FAILED
    return COMPLETED


def _finalize(state: dict) -> AgentResult:
    """Turn the end state into an AgentResult and close out session memory."""
    reply = state["reply"]
    state["session_memory"].add("assistant", reply)
    delegate = state.get("delegate")
    return AgentResult(
        reply=reply,
        steps=state["steps"],
        tools_used=state.get("tools_used", []),
        tokens_used=state.get("tokens_used", 0),
        status=_status_for(state),
        pending_action=state.get("pending_action"),
        delegated_to=delegate.name if delegate is not None else None,
    )


def stream_agent(
    *,
    db: Session,
    org_id: int,
    user_id: int,
    conversation_id: int,
    message: str,
    agent_name: str = "Assistant",
    enabled_tools: list[str] | None = None,
    teammates: list[Teammate] | None = None,
    requires_approval: bool = False,
    pre_approved: bool = False,
    forced_intent: tuple[str, dict[str, Any]] | None = None,
    record_user_turn: bool = True,
) -> Iterator[AgentEvent]:
    """Run one turn, yielding a step event per node and then the final result."""
    state = _initial_state(
        db=db,
        org_id=org_id,
        user_id=user_id,
        conversation_id=conversation_id,
        message=message,
        agent_name=agent_name,
        enabled_tools=enabled_tools,
        teammates=teammates,
        requires_approval=requires_approval,
        pre_approved=pre_approved,
        forced_intent=forced_intent,
        record_user_turn=record_user_turn,
    )
    for node, current in _GRAPH.stream(state):
        last_detail = current["steps"][-1]["detail"]
        state = current
        yield AgentEvent(type="step", node=node, detail=last_detail)
    yield AgentEvent(type="result", result=_finalize(state))


def run_agent(
    *,
    db: Session,
    org_id: int,
    user_id: int,
    conversation_id: int,
    message: str,
    agent_name: str = "Assistant",
    enabled_tools: list[str] | None = None,
    teammates: list[Teammate] | None = None,
    requires_approval: bool = False,
    pre_approved: bool = False,
    forced_intent: tuple[str, dict[str, Any]] | None = None,
    record_user_turn: bool = True,
) -> AgentResult:
    """Execute one agent turn through the state graph and return the result."""
    result: AgentResult | None = None
    for event in stream_agent(
        db=db,
        org_id=org_id,
        user_id=user_id,
        conversation_id=conversation_id,
        message=message,
        agent_name=agent_name,
        enabled_tools=enabled_tools,
        teammates=teammates,
        requires_approval=requires_approval,
        pre_approved=pre_approved,
        forced_intent=forced_intent,
        record_user_turn=record_user_turn,
    ):
        if event.type == "result":
            result = event.result
    if result is None:  # pragma: no cover - the stream always ends with a result
        raise RuntimeError("agent stream ended without a result event")
    return result


__all__ = [
    "run_agent",
    "stream_agent",
    "AgentResult",
    "AgentEvent",
    "Teammate",
    "StateGraph",
    "END",
    "COMPLETED",
    "FAILED",
    "AWAITING_APPROVAL",
]
