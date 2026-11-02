from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import PermissionDeniedError
from app.repositories.approval_repository import ApprovalRepository
from app.schemas.approval_decision import ApprovalDecision
from app.schemas.approval_decision_request import ApprovalDecisionRequest
from app.schemas.approval_response import ApprovalResponse
from app.schemas.approval_status import ApprovalStatus
from app.schemas.caller import Caller
from app.schemas.role import Role
from app.services.agent_run_service import AgentRunService


class ApprovalService:
    """Lists pending approvals and lets admins approve or reject them; the run then resumes."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        agent_run_service: AgentRunService,
    ) -> None:
        self._session_factory = session_factory
        self._runs = agent_run_service

    async def list_pending(self) -> list[ApprovalResponse]:
        async with self._session_factory() as session:
            approvals = await ApprovalRepository(session).list_pending()
        return [ApprovalResponse.model_validate(approval) for approval in approvals]

    async def decide(
        self, approval_id: str, request: ApprovalDecisionRequest, caller: Caller
    ) -> ApprovalResponse:
        if caller.role is not Role.ADMIN:
            raise PermissionDeniedError(
                "Only admins can approve or reject tool calls",
                details={"approval_id": approval_id, "role": caller.role.value},
            )
        status = ApprovalStatus.APPROVED if request.approved else ApprovalStatus.REJECTED
        async with self._session_factory() as session:
            approval = await ApprovalRepository(session).record_decision(
                approval_id, status, decided_by=caller.name, reason=request.reason
            )
        decision = ApprovalDecision(
            approved=request.approved, decided_by=caller.name, reason=request.reason
        )
        self._runs.resume_in_background(approval.run_id, decision)
        return ApprovalResponse.model_validate(approval)
