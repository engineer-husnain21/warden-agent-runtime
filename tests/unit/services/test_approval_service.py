import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import InvalidInputError, PermissionDeniedError
from app.schemas.agent_run_status import AgentRunStatus
from app.schemas.approval_decision_request import ApprovalDecisionRequest
from app.schemas.approval_status import ApprovalStatus
from app.schemas.audit_action import AuditAction
from app.schemas.caller import Caller
from app.schemas.role import Role
from app.services.agent_run_service import AgentRunService
from app.services.approval_service import ApprovalService
from app.services.audit_service import AuditService
from tests.fakes.fake_llm_client import FakeLlmClient
from tests.fakes.fake_tool_client import FakeToolClient
from tests.unit.orchestrators.orchestrator_helpers import (
    TOOLS,
    build_orchestrator,
    plan,
    review,
    select,
)

OSCAR = Caller(name="oscar", role=Role.OPERATOR)
ADA = Caller(name="ada", role=Role.ADMIN)


async def _paused_run(
    session_factory: async_sessionmaker[AsyncSession], after_resume: list[str]
) -> tuple[ApprovalService, AgentRunService, AuditService, FakeToolClient, str]:
    replies = [plan("Open an issue"), select("github.create_issue", title="Timeouts")]
    tools = FakeToolClient(tools=TOOLS, results={"github.create_issue": {"issue": {"number": 7}}})
    audit = AuditService(session_factory)
    runs = AgentRunService(
        session_factory,
        audit,
        build_orchestrator(FakeLlmClient(replies + after_resume), tools),
    )
    run = await runs.create_run("Open an issue", OSCAR)
    await runs.execute_run(run.id)
    return ApprovalService(session_factory, runs), runs, audit, tools, run.id


async def test_decide_when_non_admin_raises_permission_denied(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    approvals, *_ = await _paused_run(session_factory, [])
    [pending] = await approvals.list_pending()

    with pytest.raises(PermissionDeniedError):
        await approvals.decide(pending.id, ApprovalDecisionRequest(approved=True), OSCAR)


async def test_decide_when_admin_approves_resumes_run_to_completion(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    approvals, runs, audit, tools, run_id = await _paused_run(
        session_factory, [review(True), "## Summary\nOpened issue #7."]
    )
    [pending] = await approvals.list_pending()

    decided = await approvals.decide(pending.id, ApprovalDecisionRequest(approved=True), ADA)
    await runs.drain()

    assert (decided.status, decided.decided_by) == (ApprovalStatus.APPROVED, "ada")
    assert (await runs.get_run(run_id)).status is AgentRunStatus.COMPLETED
    assert [call.tool for call in tools.calls] == ["github.create_issue"]
    assert await approvals.list_pending() == []
    granted = [e for e in await audit.list_entries(ADA, run_id=run_id) if e.actor == "ada"]
    assert [e.action for e in granted] == [AuditAction.APPROVAL_GRANTED]


async def test_decide_when_rejected_completes_run_without_tool_call(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    approvals, runs, _, tools, run_id = await _paused_run(
        session_factory, ["## Summary\nNo issue: rejected."]
    )
    [pending] = await approvals.list_pending()

    await approvals.decide(
        pending.id, ApprovalDecisionRequest(approved=False, reason="duplicate"), ADA
    )
    await runs.drain()

    assert (await runs.get_run(run_id)).status is AgentRunStatus.COMPLETED
    assert tools.calls == []


async def test_decide_when_already_decided_raises_invalid_input(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    approvals, runs, *_ = await _paused_run(session_factory, ["## Summary\nRejected."])
    [pending] = await approvals.list_pending()
    await approvals.decide(pending.id, ApprovalDecisionRequest(approved=False), ADA)
    await runs.drain()

    with pytest.raises(InvalidInputError):
        await approvals.decide(pending.id, ApprovalDecisionRequest(approved=True), ADA)
