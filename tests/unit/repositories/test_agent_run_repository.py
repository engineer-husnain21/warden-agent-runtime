import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models import AgentRunStatus, RunStep, RunStepKind, RunStepStatus
from app.repositories.agent_run_repository import AgentRunRepository


@pytest.fixture
def repository(db_session: AsyncSession) -> AgentRunRepository:
    return AgentRunRepository(db_session)


async def test_get_by_id_when_missing_raises_not_found(repository: AgentRunRepository) -> None:
    with pytest.raises(NotFoundError):
        await repository.get_by_id("does-not-exist")


async def test_create_when_valid_persists_pending_run(repository: AgentRunRepository) -> None:
    run = await repository.create("Find failed orders", requested_by="alice", role="operator")

    loaded = await repository.get_by_id(run.id)

    assert loaded.task == "Find failed orders"
    assert loaded.status is AgentRunStatus.PENDING


async def test_update_status_when_completed_sets_report_and_completed_at(
    repository: AgentRunRepository,
) -> None:
    run = await repository.create("task", requested_by="alice", role="operator")

    updated = await repository.update_status(run.id, AgentRunStatus.COMPLETED, report="# Done")

    assert updated.report == "# Done"
    assert updated.completed_at is not None


async def test_add_step_when_called_twice_assigns_positions_in_order(
    repository: AgentRunRepository,
) -> None:
    run = await repository.create("task", requested_by="alice", role="operator")

    first = await repository.add_step(
        run.id, RunStep(kind=RunStepKind.PLAN, status=RunStepStatus.SUCCEEDED)
    )
    second = await repository.add_step(
        run.id, RunStep(kind=RunStepKind.TOOL_CALL, status=RunStepStatus.SUCCEEDED)
    )

    assert (first.position, second.position) == (0, 1)


async def test_list_by_status_when_mixed_returns_only_matching(
    repository: AgentRunRepository,
) -> None:
    waiting = await repository.create("a", requested_by="alice", role="operator")
    await repository.create("b", requested_by="alice", role="operator")
    await repository.update_status(waiting.id, AgentRunStatus.AWAITING_APPROVAL)

    runs = await repository.list_by_status(AgentRunStatus.AWAITING_APPROVAL)

    assert [run.id for run in runs] == [waiting.id]
