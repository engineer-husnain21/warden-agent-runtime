from pydantic import BaseModel, ConfigDict

from app.schemas.run_step_kind import RunStepKind


class StepMetricsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position: int
    kind: RunStepKind
    agent: str | None
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float
