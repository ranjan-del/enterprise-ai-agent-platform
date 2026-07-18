"""LangGraph agent runtime skeleton.

Defines the shape of the agent state graph described in MEMORY.md:
memory -> planning -> tool calling -> reflection -> streaming, with a
human-approval interrupt and multi-agent hand-off.

TODO: checklist "Agent runtime on LangGraph: memory, planning, tool calling,
reflection, streaming, human approval, multi-agent".
"""
from typing import Any, TypedDict

# from langgraph.graph import StateGraph, END


class AgentState(TypedDict, total=False):
    """State threaded through the graph. Placeholder fields only."""

    messages: list[dict[str, Any]]
    plan: list[str]
    scratchpad: dict[str, Any]
    pending_approval: bool


# --- Node stubs -----------------------------------------------------------

def plan_node(state: AgentState) -> AgentState:
    """Produce/refine a plan for the current objective."""
    # TODO: checklist "planning"
    return state


def tool_node(state: AgentState) -> AgentState:
    """Execute selected tool calls (see app.agents.tools)."""
    # TODO: checklist "tool calling"
    return state


def reflect_node(state: AgentState) -> AgentState:
    """Critique the last step and decide whether to continue."""
    # TODO: checklist "reflection"
    return state


def human_approval_node(state: AgentState) -> AgentState:
    """Interrupt point for human-in-the-loop approval."""
    # TODO: checklist "human approval" — use LangGraph interrupt()
    return state


def build_graph():
    """Assemble and compile the agent StateGraph.

    TODO: wire nodes/edges, attach a checkpointer (Redis/Postgres) for
    persistent memory, and enable streaming + multi-agent sub-graphs.
    """
    # graph = StateGraph(AgentState)
    # graph.add_node("plan", plan_node)
    # graph.add_node("tools", tool_node)
    # graph.add_node("reflect", reflect_node)
    # graph.add_node("approval", human_approval_node)
    # ... add_edge(...) / add_conditional_edges(...)
    # return graph.compile(checkpointer=...)
    raise NotImplementedError("build_graph not implemented")
