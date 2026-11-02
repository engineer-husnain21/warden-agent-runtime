from typing import Any

from pydantic import BaseModel, Field

from app.schemas.llm_usage import LlmUsage
from app.schemas.policy_decision import PolicyDecision
from app.schemas.run_step_kind import RunStepKind
from app.schemas.run_step_status import RunStepStatus


class StepEvent(BaseModel):
    """One thing that happened in a run, yielded by the orchestrator as it happens.

    The service turns each event into a RunStep row (with its token, latency and cost totals)
    and, where relevant, an audit entry.
    """

    run_id: str
    kind: RunStepKind
    status: RunStepStatus
    agent: str | None = None
    step_index: int | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    policy_decision: PolicyDecision | None = None
    usage: list[LlmUsage] = Field(default_factory=list)

    @property
    def input_tokens(self) -> int:
        return sum(u.input_tokens for u in self.usage)

    @property
    def output_tokens(self) -> int:
        return sum(u.output_tokens for u in self.usage)

    @property
    def latency_ms(self) -> float:
        return sum(u.latency_ms for u in self.usage)

    @property
    def cost_usd(self) -> float:
        return sum(u.cost_usd for u in self.usage)
