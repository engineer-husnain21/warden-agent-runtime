from collections.abc import Sequence
from typing import Protocol

from app.schemas.llm_message import LlmMessage
from app.schemas.llm_response import LlmResponse


class LlmClient(Protocol):
    """Any chat LLM provider. Implementations report usage (tokens, latency, cost) per call."""

    async def complete(
        self,
        messages: Sequence[LlmMessage],
        *,
        json_mode: bool = False,
        temperature: float = 0.0,
    ) -> LlmResponse: ...
