import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import PermissionDeniedError
from app.schemas.audit_action import AuditAction
from app.schemas.caller import Caller
from app.schemas.policy_decision import PolicyDecision
from app.schemas.role import Role
from app.schemas.run_step_kind import RunStepKind
from app.schemas.run_step_status import RunStepStatus
from app.schemas.step_event import StepEvent
from app.services.audit_service import AuditService

ADMIN = Caller(name="ada", role=Role.ADMIN)


@pytest.fixture
def service(session_factory: async_sessionmaker[AsyncSession]) -> AuditService:
    return AuditService(session_factory)


async def test_record_when_called_appends_entry(service: AuditService) -> None:
    await service.record(
        actor="oscar", role="operator", action=AuditAction.RUN_CREATED, run_id="r1"
    )

    entries = await service.list_entries(ADMIN)

    assert [(e.actor, e.action) for e in entries] == [("oscar", AuditAction.RUN_CREATED)]


async def test_list_entries_when_not_admin_raises_permission_denied(service: AuditService) -> None:
    with pytest.raises(PermissionDeniedError):
        await service.list_entries(Caller(name="oscar", role=Role.OPERATOR))


async def test_record_event_when_denied_permission_check_audits_denial(
    service: AuditService,
) -> None:
    event = StepEvent(
        run_id="r1",
        kind=RunStepKind.PERMISSION_CHECK,
        status=RunStepStatus.DENIED,
        tool_name="github.create_issue",
        tool_arguments={"title": "t"},
        policy_decision=PolicyDecision.DENY,
    )

    await service.record_event(event, actor="vera", role="viewer")

    [entry] = await service.list_entries(ADMIN, run_id="r1")
    assert entry.action is AuditAction.TOOL_CALL_DENIED
    assert (entry.actor, entry.tool_name, entry.decision) == ("vera", "github.create_issue", "deny")


async def test_record_event_when_approval_granted_records_the_approver(
    service: AuditService,
) -> None:
    event = StepEvent(
        run_id="r1",
        kind=RunStepKind.APPROVAL,
        status=RunStepStatus.SUCCEEDED,
        tool_name="github.create_issue",
        output={"approved": True, "decided_by": "ada", "reason": None},
    )

    await service.record_event(event, actor="oscar", role="operator")

    [entry] = await service.list_entries(ADMIN)
    assert (entry.action, entry.actor, entry.role) == (AuditAction.APPROVAL_GRANTED, "ada", "admin")


async def test_record_event_when_plan_event_writes_nothing(service: AuditService) -> None:
    event = StepEvent(run_id="r1", kind=RunStepKind.PLAN, status=RunStepStatus.SUCCEEDED)

    await service.record_event(event, actor="oscar", role="operator")

    assert await service.list_entries(ADMIN) == []


async def test_record_when_result_huge_stores_it_cut_off(service: AuditService) -> None:
    await service.record(
        actor="a", role="admin", action=AuditAction.TOOL_CALL_SUCCEEDED, result={"x": "y" * 10_000}
    )

    [entry] = await service.list_entries(ADMIN)
    assert entry.result is not None
    assert entry.result["original_size"] > 10_000
