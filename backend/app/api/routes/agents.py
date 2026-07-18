"""Agent configuration + execution routes.

TODO: checklist "Agent runtime on LangGraph" and "Execution history".
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_agents() -> dict:
    """List agents configured for the organization."""
    # TODO: implement agent listing
    return {"detail": "TODO: implement list_agents"}


@router.post("")
async def create_agent() -> dict:
    """Create/configure a new agent (tools, memory, prompts)."""
    # TODO: implement agent configuration
    return {"detail": "TODO: implement create_agent"}


@router.post("/{agent_id}/run")
async def run_agent(agent_id: str) -> dict:
    """Execute an agent via the LangGraph runtime."""
    # TODO: checklist "planning, tool calling, reflection, human approval, multi-agent"
    return {"detail": "TODO: implement run_agent", "agent_id": agent_id}


@router.get("/{agent_id}/executions")
async def list_executions(agent_id: str) -> dict:
    """List execution history for an agent."""
    # TODO: checklist "Execution history + analytics"
    return {"detail": "TODO: implement list_executions", "agent_id": agent_id}
