from collections.abc import Sequence
from typing import Any

from sqlalchemy import event, select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapper

from app.core.exceptions import PermissionDeniedError
from app.models import AuditAction, AuditLogEntry
from app.repositories.base_repository import BaseRepository


class AuditLogRepository(BaseRepository[AuditLogEntry]):
    """Append-only: entries can be added and read, never changed or removed."""

    model = AuditLogEntry

    async def append(
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
    ) -> AuditLogEntry:
        entry = AuditLogEntry(
            run_id=run_id,
            actor=actor,
            role=role,
            action=action,
            tool_name=tool_name,
            tool_arguments=tool_arguments,
            decision=decision,
            result=result,
        )
        return await self._save(entry)

    async def list_entries(
        self, run_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> Sequence[AuditLogEntry]:
        query = select(AuditLogEntry).order_by(AuditLogEntry.id).limit(limit).offset(offset)
        if run_id is not None:
            query = query.where(AuditLogEntry.run_id == run_id)
        return (await self._session.scalars(query)).all()


def _reject_change(_mapper: Mapper[Any], _connection: Connection, target: AuditLogEntry) -> None:
    raise PermissionDeniedError(
        "Audit log entries are append-only", details={"audit_log_entry_id": target.id}
    )


# Guard the ORM path too, so no code can update or delete an entry through a session.
event.listen(AuditLogEntry, "before_update", _reject_change)
event.listen(AuditLogEntry, "before_delete", _reject_change)
