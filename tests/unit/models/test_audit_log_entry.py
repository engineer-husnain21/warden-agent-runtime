from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditAction, AuditLogEntry


async def test_audit_log_entry_when_created_sets_timestamp(db_session: AsyncSession) -> None:
    entry = AuditLogEntry(
        run_id="run-that-may-be-deleted",
        actor="alice",
        role="admin",
        action=AuditAction.APPROVAL_GRANTED,
        tool_name="github.create_issue",
        tool_arguments={"title": "Payment timeouts"},
        decision="approved",
    )
    db_session.add(entry)
    await db_session.flush()

    assert entry.id is not None
    assert entry.created_at is not None
    assert entry.action is AuditAction.APPROVAL_GRANTED
