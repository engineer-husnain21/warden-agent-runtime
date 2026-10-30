from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, str_enum_type, utc_now
from app.models.audit_action import AuditAction


class AuditLogEntry(Base):
    """One append-only audit record: who asked, which tool, which arguments, which decision, result.

    `run_id` has no foreign key on purpose: audit entries must outlive the runs they describe.
    """

    __tablename__ = "audit_log_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str | None] = mapped_column(String(36), index=True, default=None)
    actor: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    action: Mapped[AuditAction] = mapped_column(str_enum_type(AuditAction))
    tool_name: Mapped[str | None] = mapped_column(String(100), default=None)
    tool_arguments: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    decision: Mapped[str | None] = mapped_column(String(20), default=None)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
