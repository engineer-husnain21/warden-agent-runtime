import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PermissionDeniedError
from app.models import AuditAction
from app.repositories.audit_log_repository import AuditLogRepository


@pytest.fixture
def repository(db_session: AsyncSession) -> AuditLogRepository:
    return AuditLogRepository(db_session)


def test_repository_when_inspected_has_no_update_or_delete() -> None:
    public_methods = {name for name in dir(AuditLogRepository) if not name.startswith("_")}

    assert public_methods == {"append", "get_by_id", "list_entries", "model"}


async def test_list_entries_when_appended_returns_in_insert_order(
    repository: AuditLogRepository,
) -> None:
    await repository.append(
        actor="bob", role="operator", action=AuditAction.RUN_CREATED, run_id="r1"
    )
    await repository.append(
        actor="bob", role="operator", action=AuditAction.RUN_COMPLETED, run_id="r1"
    )
    await repository.append(actor="eve", role="viewer", action=AuditAction.RUN_CREATED, run_id="r2")

    entries = await repository.list_entries(run_id="r1")

    assert [entry.action for entry in entries] == [
        AuditAction.RUN_CREATED,
        AuditAction.RUN_COMPLETED,
    ]


async def test_flush_when_entry_modified_raises_permission_denied(
    db_session: AsyncSession, repository: AuditLogRepository
) -> None:
    entry = await repository.append(actor="bob", role="operator", action=AuditAction.RUN_CREATED)
    entry.actor = "mallory"

    with pytest.raises(PermissionDeniedError):
        await db_session.flush()


async def test_flush_when_entry_deleted_raises_permission_denied(
    db_session: AsyncSession, repository: AuditLogRepository
) -> None:
    entry = await repository.append(actor="bob", role="operator", action=AuditAction.RUN_CREATED)
    await db_session.delete(entry)

    with pytest.raises(PermissionDeniedError):
        await db_session.flush()
