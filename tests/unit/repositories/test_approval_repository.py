import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidInputError
from app.models import Approval, ApprovalStatus
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.approval_repository import ApprovalRepository


@pytest.fixture
def repository(db_session: AsyncSession) -> ApprovalRepository:
    return ApprovalRepository(db_session)


async def _new_approval(db_session: AsyncSession, repository: ApprovalRepository) -> Approval:
    run = await AgentRunRepository(db_session).create("task", requested_by="bob", role="operator")
    return await repository.create(
        run_id=run.id,
        step_position=1,
        tool_name="github.create_issue",
        tool_arguments={"title": "Timeouts"},
        requested_by="bob",
    )


async def test_list_pending_when_mixed_statuses_returns_only_pending(
    db_session: AsyncSession, repository: ApprovalRepository
) -> None:
    pending = await _new_approval(db_session, repository)
    decided = await _new_approval(db_session, repository)
    await repository.record_decision(decided.id, ApprovalStatus.APPROVED, decided_by="admin")

    approvals = await repository.list_pending()

    assert [approval.id for approval in approvals] == [pending.id]


async def test_record_decision_when_pending_stores_decider_and_time(
    db_session: AsyncSession, repository: ApprovalRepository
) -> None:
    approval = await _new_approval(db_session, repository)

    decided = await repository.record_decision(
        approval.id, ApprovalStatus.REJECTED, decided_by="admin", reason="Too noisy"
    )

    assert decided.status is ApprovalStatus.REJECTED
    assert decided.decided_by == "admin"
    assert decided.decision_reason == "Too noisy"
    assert decided.decided_at is not None


async def test_record_decision_when_already_decided_raises_invalid_input(
    db_session: AsyncSession, repository: ApprovalRepository
) -> None:
    approval = await _new_approval(db_session, repository)
    await repository.record_decision(approval.id, ApprovalStatus.APPROVED, decided_by="admin")

    with pytest.raises(InvalidInputError):
        await repository.record_decision(approval.id, ApprovalStatus.REJECTED, decided_by="admin")


async def test_get_pending_for_run_when_none_returns_none(repository: ApprovalRepository) -> None:
    assert await repository.get_pending_for_run("no-such-run") is None
