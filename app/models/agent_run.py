import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, str_enum_type, utc_now
from app.models.agent_run_status import AgentRunStatus

if TYPE_CHECKING:
    from app.models.run_step import RunStep


class AgentRun(Base):
    """One task submitted by a caller, from creation to final report."""

    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task: Mapped[str] = mapped_column(Text)
    requested_by: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    status: Mapped[AgentRunStatus] = mapped_column(
        str_enum_type(AgentRunStatus), default=AgentRunStatus.PENDING, index=True
    )
    report: Mapped[str | None] = mapped_column(Text, default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    steps: Mapped[list["RunStep"]] = relationship(
        back_populates="run",
        order_by="RunStep.position",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
