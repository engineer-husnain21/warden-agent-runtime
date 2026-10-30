import time
from collections.abc import Sequence
from typing import Any

import httpx

from app.clients.backoff import retry_with_backoff
from app.clients.pricing import estimate_cost_usd
from app.core.exceptions import ExternalServiceError
from app.schemas.llm_message import LlmMessage
from app.schemas.llm_response import LlmResponse
from app.schemas.llm_usage import LlmUsage


class GroqLlmClient:
    """LlmClient for Groq's OpenAI-compatible chat completions API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        input_price_per_mtok: float,
        output_price_per_mtok: float,
        http_client: httpx.AsyncClient,
        max_attempts: int = 4,
        retry_base_delay: float = 0.5,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._input_price = input_price_per_mtok
        self._output_price = output_price_per_mtok
        self._http = http_client
        self._max_attempts = max_attempts
        self._retry_base_delay = retry_base_delay

    async def complete(
        self,
        messages: Sequence[LlmMessage],
        *,
        json_mode: bool = False,
        temperature: float = 0.0,
    ) -> LlmResponse:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [message.model_dump() for message in messages],
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        started = time.perf_counter()
        try:
            data = await retry_with_backoff(
                lambda: self._post(payload),
                max_attempts=self._max_attempts,
                base_delay=self._retry_base_delay,
            )
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                "Groq request failed", details={"provider": "groq", "error": str(error)}
            ) from error
        latency_ms = (time.perf_counter() - started) * 1000

        try:
            text = data["choices"][0]["message"]["content"]
            input_tokens = int(data["usage"]["prompt_tokens"])
            output_tokens = int(data["usage"]["completion_tokens"])
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ExternalServiceError(
                "Groq returned an unexpected response", details={"provider": "groq"}
            ) from error

        usage = LlmUsage(
            model=self._model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=estimate_cost_usd(
                input_tokens, output_tokens, self._input_price, self._output_price
            ),
        )
        return LlmResponse(text=str(text), usage=usage)

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._http.post(
            self._url, json=payload, headers={"Authorization": f"Bearer {self._api_key}"}
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data
