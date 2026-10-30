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

_GEMINI_ROLES = {"user": "user", "assistant": "model"}


class GeminiLlmClient:
    """LlmClient for the Google Gemini `generateContent` API."""

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
        self._url = f"{base_url.rstrip('/')}/models/{model}:generateContent"
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
        payload = _build_payload(messages, json_mode=json_mode, temperature=temperature)

        started = time.perf_counter()
        try:
            data = await retry_with_backoff(
                lambda: self._post(payload),
                max_attempts=self._max_attempts,
                base_delay=self._retry_base_delay,
            )
        except httpx.HTTPError as error:
            raise ExternalServiceError(
                "Gemini request failed", details={"provider": "gemini", "error": str(error)}
            ) from error
        latency_ms = (time.perf_counter() - started) * 1000

        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(str(part.get("text", "")) for part in parts)
            metadata = data["usageMetadata"]
            input_tokens = int(metadata["promptTokenCount"])
            # Thinking tokens are billed as output tokens.
            output_tokens = int(metadata.get("candidatesTokenCount", 0)) + int(
                metadata.get("thoughtsTokenCount", 0)
            )
        except (KeyError, IndexError, TypeError, ValueError, AttributeError) as error:
            raise ExternalServiceError(
                "Gemini returned an unexpected response", details={"provider": "gemini"}
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
        return LlmResponse(text=text, usage=usage)

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._http.post(
            self._url, json=payload, headers={"x-goog-api-key": self._api_key}
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data


def _build_payload(
    messages: Sequence[LlmMessage], *, json_mode: bool, temperature: float
) -> dict[str, Any]:
    system_text = "\n\n".join(m.content for m in messages if m.role == "system")
    contents = [
        {"role": _GEMINI_ROLES[m.role], "parts": [{"text": m.content}]}
        for m in messages
        if m.role != "system"
    ]
    generation_config: dict[str, Any] = {"temperature": temperature}
    if json_mode:
        generation_config["responseMimeType"] = "application/json"

    payload: dict[str, Any] = {"contents": contents, "generationConfig": generation_config}
    if system_text:
        payload["systemInstruction"] = {"parts": [{"text": system_text}]}
    return payload
