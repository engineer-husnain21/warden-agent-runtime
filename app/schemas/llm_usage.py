from pydantic import BaseModel, Field


class LlmUsage(BaseModel):
    """Tokens, latency and estimated cost of one LLM call."""

    model: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: float = Field(ge=0)
    cost_usd: float = Field(ge=0)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
