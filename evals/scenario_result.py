from pydantic import BaseModel


class ScenarioResult(BaseModel):
    """How one scenario went: pass/fail with reasons, tool-call accuracy and what the run used."""

    scenario_id: str
    passed: bool
    tool_accuracy: float
    status: str
    failures: list[str] = []
    picked_tools: list[str] = []
    run_id: str | None = None
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    llm_latency_ms: float = 0.0
    cost_usd: float = 0.0
    duration_seconds: float = 0.0
    attempts: int = 1
