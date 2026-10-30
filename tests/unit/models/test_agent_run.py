from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentRun, AgentRunStatus, RunStep, RunStepKind, RunStepStatus


def _new_run() -> AgentRun:
    return AgentRun(task="Find failed orders", requested_by="alice", role="operator")


async def test_agent_run_when_created_has_pending_status(db_session: AsyncSession) -> None:
    run = _new_run()
    db_session.add(run)
    await db_session.flush()

    assert run.status is AgentRunStatus.PENDING
    assert len(run.id) == 36
    assert run.created_at is not None
    assert run.report is None


async def test_agent_run_when_steps_added_loads_them_in_position_order(
    db_session: AsyncSession,
) -> None:
    run = _new_run()
    run.steps = [
        RunStep(position=1, kind=RunStepKind.TOOL_CALL, status=RunStepStatus.SUCCEEDED),
        RunStep(position=0, kind=RunStepKind.PLAN, status=RunStepStatus.SUCCEEDED),
    ]
    db_session.add(run)
    await db_session.commit()
    db_session.expunge_all()

    loaded = (await db_session.execute(select(AgentRun))).scalar_one()

    assert [step.kind for step in loaded.steps] == [RunStepKind.PLAN, RunStepKind.TOOL_CALL]
    assert loaded.steps[0].input_tokens == 0
    assert loaded.steps[0].cost_usd == 0.0
