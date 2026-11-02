from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_audit_service, get_current_caller
from app.schemas.audit_log_entry_response import AuditLogEntryResponse
from app.schemas.caller import Caller
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-log-entries", tags=["audit-log"])

Audit = Annotated[AuditService, Depends(get_audit_service)]
CurrentCaller = Annotated[Caller, Depends(get_current_caller)]


@router.get("")
async def list_audit_log_entries(
    caller: CurrentCaller,
    service: Audit,
    run_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AuditLogEntryResponse]:
    """The append-only audit log, oldest first (admins only)."""
    return await service.list_entries(caller, run_id=run_id, limit=limit, offset=offset)
