from collections.abc import Sequence

from app.schemas.llm_message import LlmMessage
from app.schemas.llm_response import LlmResponse
from app.schemas.llm_usage import LlmUsage


class FakeLlmClient:
    """Returns scripted replies in order and records every call."""

    def __init__(self, replies: Sequence[str], model: str = "fake-model") -> None:
        self._replies = list(replies)
        self._model = model
        self.calls: list[list[LlmMessage]] = []

    async def complete(
        self,
        messages: Sequence[LlmMessage],
        *,
        json_mode: bool = False,
        temperature: float = 0.0,
    ) -> LlmResponse:
        self.calls.append(list(messages))
        if not self._replies:
            raise AssertionError("FakeLlmClient ran out of scripted replies")
        text = self._replies.pop(0)
        usage = LlmUsage(
            model=self._model,
            input_tokens=sum(len(message.content.split()) for message in messages),
            output_tokens=len(text.split()),
            latency_ms=1.0,
            cost_usd=0.0,
        )
        return LlmResponse(text=text, usage=usage)
