from app.schemas.agents.base_agent_output import BaseAgentOutput


class StepReviewerOutput(BaseAgentOutput):
    """`ok=False` means the step should be retried; `feedback` says what to change."""

    ok: bool
    feedback: str = ""
