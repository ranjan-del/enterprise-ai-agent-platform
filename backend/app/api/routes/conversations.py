"""Conversation + message routes (chat surface).

TODO: checklist "Dashboard: Conversations" and "streaming".
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_conversations() -> dict:
    """List conversations for the current user/org."""
    # TODO: implement conversation listing
    return {"detail": "TODO: implement list_conversations"}


@router.post("")
async def create_conversation() -> dict:
    """Start a new conversation thread."""
    # TODO: implement conversation creation
    return {"detail": "TODO: implement create_conversation"}


@router.get("/{conversation_id}/messages")
async def list_messages(conversation_id: str) -> dict:
    """List messages in a conversation."""
    # TODO: implement message history retrieval
    return {"detail": "TODO: implement list_messages", "conversation_id": conversation_id}


@router.post("/{conversation_id}/messages")
async def post_message(conversation_id: str) -> dict:
    """Send a message and stream the agent response."""
    # TODO: checklist "streaming" — return an SSE/WebSocket stream from the graph.
    return {"detail": "TODO: implement post_message", "conversation_id": conversation_id}
