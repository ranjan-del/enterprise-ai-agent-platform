"""Tool registry routes.

TODO: checklist "Tool integrations: GitHub, calculator, weather, Gmail,
Google Drive, database, file system".
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_tools() -> dict:
    """List available tools the agents can call."""
    # TODO: enumerate registered tools from app.agents.tools
    return {"detail": "TODO: implement list_tools"}


@router.post("/{tool_name}/invoke")
async def invoke_tool(tool_name: str) -> dict:
    """Directly invoke a tool (debug / manual trigger)."""
    # TODO: dispatch to the concrete tool implementation
    return {"detail": "TODO: implement invoke_tool", "tool_name": tool_name}
