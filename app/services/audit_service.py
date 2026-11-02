import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import PermissionDeniedError
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.audit_action import AuditAction
from app.schemas.audit_log_entry_response import AuditLogEntryResponse
from app.schemas.caller import Caller
from app.schemas.role import Role
from app.schemas.run_step_kind import RunStepKind
from app.schemas.run_step_status import RunStepStatus
from app.schemas.step_event import StepEvent

MAX_AUDIT_RESULT_CHARS = 4000

# (step kind, step status) -> audit action. Other events are part of the trace, not the audit log.
_EVENT_ACTIONS = {
    (RunStepKind.PERMISSION_CHECK, RunStepStatus.SUCCEEDED): AuditAction.TOOL_CALL_ALLOWED,
    (RunStepKind.PERMISSION_CHECK, RunStepStatus.DENIED): AuditAction.TOOL_CALL_DENIED,
    (RunStepKind.APPROVAL, RunStepStatus.AWAITING_APPROVAL): AuditAction.APPROVAL_REQUESTED,
    (RunStepKind.APPROVAL, RunStepStatus.SUCCEEDED): AuditAction.APPROVAL_GRANTED,
    (RunStepKind.APPROVAL, RunStepStatus.DENIED): AuditAction.APPROVAL_REJECTED,
    (RunStepKind.TOOL_CALL, RunStepStatus.SUCCEEDED): AuditAction.TOOL_CALL_SUCCEEDED,
    (RunStepKind.TOOL_CALL, RunStepStatus.FAILED): AuditAction.TOOL_CALL_FAILED,
}


class AuditService:
    """Writes the append-only audit log and serves it to admins only."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record(
        self,
        *,
        actor: str,
        role: str,
        action: AuditAction,
        run_id: str | None = None,
        tool_name: str | None = None,
        tool_arguments: dict[str, Any] | None = None,
        decision: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        async with self._session_factory() as session:
            await AuditLogRepository(session).append(
                actor=actor,
                role=role,
                action=action,
                run_id=run_id,
                tool_name=tool_name,
                tool_arguments=tool_arguments,
                decision=decision,
                result=_bounded(result),
            )

    async def record_event(self, event: StepEvent, actor: str, role: str) -> None:
        """Audit a step event if it is a tool decision or a tool call; ignore the rest."""
        action = _EVENT_ACTIONS.get((event.kind, event.status))
        if action is None:
            return
        decided_by = (event.output or {}).get("decided_by")
        is_decision = action in {AuditAction.APPROVAL_GRANTED, AuditAction.APPROVAL_REJECTED}
        await self.record(
            actor=decided_by if is_decision and decided_by else actor,
            role=Role.ADMIN.value if is_decision else role,
            action=action,
            run_id=event.run_id,
            tool_name=event.tool_name,
            tool_arguments=event.tool_arguments,
            decision=event.policy_decision.value if event.policy_decision else None,
            result=event.output if event.kind is RunStepKind.TOOL_CALL or is_decision else None,
        )

    async def list_entries(
        self, caller: Caller, run_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[AuditLogEntryResponse]:
        if caller.role is not Role.ADMIN:
            raise PermissionDeniedError("Only admins can read the audit log")
        async with self._session_factory() as session:
            entries = await AuditLogRepository(session).list_entries(run_id, limit, offset)
        return [AuditLogEntryResponse.model_validate(entry) for entry in entries]


def _bounded(result: dict[str, Any] | None) -> dict[str, Any] | None:
    """Keep audit rows small: very large tool results are stored cut off."""
    if result is None:
        return None
    text = json.dumps(result, default=str)
    if len(text) <= MAX_AUDIT_RESULT_CHARS:
        return result
    return {"truncated": text[:MAX_AUDIT_RESULT_CHARS], "original_size": len(text)}
