from pydantic import BaseModel

from app.schemas.step_metrics_response import StepMetricsResponse


class AgentRunMetricsResponse(BaseModel):
    """Tokens, LLM latency and estimated cost, per step and for the whole run."""

    run_id: str
    steps: list[StepMetricsResponse]
    llm_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_latency_ms: float
    total_cost_usd: float
