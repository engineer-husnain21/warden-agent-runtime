from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentRun, Approval, ApprovalStatus


async def test_approval_when_created_is_pending_and_undecided(db_session: AsyncSession) -> None:
    run = AgentRun(task="Open issues", requested_by="bob", role="operator")
    db_session.add(run)
    await db_session.flush()
    approval = Approval(
        run_id=run.id,
        step_position=2,
        tool_name="github.create_issue",
        tool_arguments={"title": "Payment timeouts"},
        requested_by="bob",
    )
    db_session.add(approval)
    await db_session.flush()

    assert approval.status is ApprovalStatus.PENDING
    assert approval.decided_by is None
    assert approval.decided_at is None
    assert len(approval.id) == 36
