from pydantic import BaseModel, Field

from app.schemas.llm_usage import LlmUsage


class BaseAgentOutput(BaseModel):
    """Every agent output carries the usage of the LLM calls that produced it."""

    usage: list[LlmUsage] = Field(default_factory=list)
