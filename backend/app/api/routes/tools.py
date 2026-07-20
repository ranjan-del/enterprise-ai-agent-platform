"""Tool routes — list available tools and invoke one directly (offline)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.tools.base import ToolContext, ToolError
from app.agents.tools.registry import all_tools, invoke_tool
from app.db.session import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.agent import ToolInvokeRequest, ToolInvokeResponse, ToolOut

router = APIRouter()


@router.get("", response_model=list[ToolOut])
def list_tools(current_user: User = Depends(get_current_user)):
    return [ToolOut(**t.to_dict()) for t in all_tools()]


@router.post("/{name}/invoke", response_model=ToolInvokeResponse)
def invoke(
    name: str,
    payload: ToolInvokeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = ToolContext(db=db, org_id=current_user.org_id, user_id=current_user.id)
    try:
        result = invoke_tool(name, payload.params, ctx)
    except ToolError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return ToolInvokeResponse(tool=name, result=result)
