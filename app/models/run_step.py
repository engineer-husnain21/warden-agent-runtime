from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, str_enum_type, utc_now
from app.models.run_step_kind import RunStepKind
from app.models.run_step_status import RunStepStatus

if TYPE_CHECKING:
    from app.models.agent_run import AgentRun


class RunStep(Base):
    """One recorded step of a run (plan, tool call, review, ...) with its usage numbers."""

    __tablename__ = "run_steps"
    __table_args__ = (UniqueConstraint("run_id", "position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    kind: Mapped[RunStepKind] = mapped_column(str_enum_type(RunStepKind))
    status: Mapped[RunStepStatus] = mapped_column(str_enum_type(RunStepStatus))
    agent: Mapped[str | None] = mapped_column(String(50), default=None)
    tool_name: Mapped[str | None] = mapped_column(String(100), default=None)
    tool_arguments: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    policy_decision: Mapped[str | None] = mapped_column(String(20), default=None)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    run: Mapped["AgentRun"] = relationship(back_populates="steps")
