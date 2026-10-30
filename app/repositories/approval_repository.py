from collections.abc import Sequence
from typing import Any

from sqlalchemy import select

from app.core.exceptions import InvalidInputError
from app.db.base import utc_now
from app.models import Approval, ApprovalStatus
from app.repositories.base_repository import BaseRepository


class ApprovalRepository(BaseRepository[Approval]):
    model = Approval

    async def create(
        self,
        run_id: str,
        step_position: int,
        tool_name: str,
        tool_arguments: dict[str, Any],
        requested_by: str,
    ) -> Approval:
        approval = Approval(
            run_id=run_id,
            step_position=step_position,
            tool_name=tool_name,
            tool_arguments=tool_arguments,
            requested_by=requested_by,
        )
        return await self._save(approval)

    async def list_pending(self) -> Sequence[Approval]:
        query = (
            select(Approval)
            .where(Approval.status == ApprovalStatus.PENDING)
            .order_by(Approval.created_at)
        )
        return (await self._session.scalars(query)).all()

    async def get_pending_for_run(self, run_id: str) -> Approval | None:
        query = select(Approval).where(
            Approval.run_id == run_id, Approval.status == ApprovalStatus.PENDING
        )
        return await self._session.scalar(query)

    async def record_decision(
        self,
        approval_id: str,
        status: ApprovalStatus,
        decided_by: str,
        reason: str | None = None,
    ) -> Approval:
        """Store a decision once. Deciding an already-decided approval is rejected."""
        approval = await self.get_by_id(approval_id)
        if approval.status is not ApprovalStatus.PENDING:
            raise InvalidInputError(
                f"Approval {approval_id} is already {approval.status}",
                details={"approval_id": approval_id, "status": approval.status.value},
            )
        approval.status = status
        approval.decided_by = decided_by
        approval.decision_reason = reason
        approval.decided_at = utc_now()
        return await self._save(approval)
