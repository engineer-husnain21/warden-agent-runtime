import json
from collections.abc import Callable

import httpx
import pytest

from app.clients.groq_llm_client import GroqLlmClient
from app.clients.llm_client import LlmClient
from app.core.exceptions import ExternalServiceError
from app.schemas.llm_message import LlmMessage

Handler = Callable[[httpx.Request], httpx.Response]

OK_BODY = {
    "choices": [{"message": {"role": "assistant", "content": '{"steps": []}'}}],
    "usage": {"prompt_tokens": 1000, "completion_tokens": 500},
}


def _client(handler: Handler) -> GroqLlmClient:
    return GroqLlmClient(
        api_key="test-key",
        model="llama-test",
        base_url="https://groq.test/openai/v1/",
        input_price_per_mtok=0.6,
        output_price_per_mtok=0.8,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        retry_base_delay=0.0,
    )


MESSAGES = [LlmMessage(role="user", content="Plan this")]


async def test_complete_when_ok_returns_tokens_and_cost() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=OK_BODY)

    client: LlmClient = _client(handler)
    response = await client.complete(MESSAGES, json_mode=True)

    assert response.text == '{"steps": []}'
    assert response.usage.input_tokens == 1000
    assert response.usage.output_tokens == 500
    assert response.usage.cost_usd == pytest.approx((1000 * 0.6 + 500 * 0.8) / 1_000_000)
    request = seen[0]
    assert str(request.url) == "https://groq.test/openai/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-key"
    payload = json.loads(request.content)
    assert payload["model"] == "llama-test"
    assert payload["response_format"] == {"type": "json_object"}


async def test_complete_when_rate_limited_once_retries_and_succeeds() -> None:
    responses = [httpx.Response(429), httpx.Response(200, json=OK_BODY)]

    response = await _client(lambda _request: responses.pop(0)).complete(MESSAGES)

    assert response.usage.output_tokens == 500


async def test_complete_when_unauthorized_raises_external_service_error() -> None:
    client = _client(lambda _request: httpx.Response(401, json={"error": "bad key"}))

    with pytest.raises(ExternalServiceError) as caught:
        await client.complete(MESSAGES)

    assert "test-key" not in str(caught.value.details)


async def test_complete_when_body_malformed_raises_external_service_error() -> None:
    client = _client(lambda _request: httpx.Response(200, json={"choices": []}))

    with pytest.raises(ExternalServiceError):
        await client.complete(MESSAGES)
