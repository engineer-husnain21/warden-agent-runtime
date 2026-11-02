from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import get_approval_service, get_current_caller
from app.schemas.approval_decision_request import ApprovalDecisionRequest
from app.schemas.approval_response import ApprovalResponse
from app.schemas.caller import Caller
from app.services.approval_service import ApprovalService

router = APIRouter(prefix="/approvals", tags=["approvals"])

Approvals = Annotated[ApprovalService, Depends(get_approval_service)]
CurrentCaller = Annotated[Caller, Depends(get_current_caller)]


@router.get("")
async def list_pending_approvals(
    _caller: CurrentCaller, service: Approvals
) -> list[ApprovalResponse]:
    """Tool calls waiting for a human decision, oldest first."""
    return await service.list_pending()


@router.post("/{approval_id}/decisions")
async def decide_approval(
    approval_id: str, body: ApprovalDecisionRequest, caller: CurrentCaller, service: Approvals
) -> ApprovalResponse:
    """Approve or reject (admins only). The paused run resumes in the background."""
    return await service.decide(approval_id, body, caller)
