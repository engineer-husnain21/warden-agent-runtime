import json
from collections.abc import Callable

import httpx
import pytest

from app.clients.gemini_llm_client import GeminiLlmClient
from app.clients.llm_client import LlmClient
from app.core.exceptions import ExternalServiceError
from app.schemas.llm_message import LlmMessage

Handler = Callable[[httpx.Request], httpx.Response]

OK_BODY = {
    "candidates": [
        {"content": {"role": "model", "parts": [{"text": '{"ok": '}, {"text": "true}"}]}}
    ],
    "usageMetadata": {
        "promptTokenCount": 1000,
        "candidatesTokenCount": 400,
        "thoughtsTokenCount": 100,
    },
}

MESSAGES = [
    LlmMessage(role="system", content="You are a planner."),
    LlmMessage(role="user", content="Plan this"),
    LlmMessage(role="assistant", content="Sure"),
]


def _client(handler: Handler) -> GeminiLlmClient:
    return GeminiLlmClient(
        api_key="test-key",
        model="gemini-test",
        base_url="https://gemini.test/v1beta",
        input_price_per_mtok=0.3,
        output_price_per_mtok=2.5,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        retry_base_delay=0.0,
    )


async def test_complete_when_ok_returns_tokens_and_cost() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=OK_BODY)

    client: LlmClient = _client(handler)
    response = await client.complete(MESSAGES, json_mode=True)

    assert response.text == '{"ok": true}'
    assert response.usage.input_tokens == 1000
    assert response.usage.output_tokens == 500
    assert response.usage.cost_usd == pytest.approx((1000 * 0.3 + 500 * 2.5) / 1_000_000)
    request = seen[0]
    assert str(request.url) == "https://gemini.test/v1beta/models/gemini-test:generateContent"
    assert request.headers["x-goog-api-key"] == "test-key"
    assert "test-key" not in str(request.url)


async def test_complete_when_called_maps_roles_and_system_instruction() -> None:
    payloads: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payloads.append(json.loads(request.content))
        return httpx.Response(200, json=OK_BODY)

    await _client(handler).complete(MESSAGES, json_mode=True)

    payload = payloads[0]
    assert payload["systemInstruction"] == {"parts": [{"text": "You are a planner."}]}
    assert payload["contents"] == [
        {"role": "user", "parts": [{"text": "Plan this"}]},
        {"role": "model", "parts": [{"text": "Sure"}]},
    ]
    assert payload["generationConfig"] == {
        "temperature": 0.0,
        "responseMimeType": "application/json",
    }


async def test_complete_when_server_error_persists_raises_external_service_error() -> None:
    client = _client(lambda _request: httpx.Response(503))

    with pytest.raises(ExternalServiceError):
        await client.complete(MESSAGES)


async def test_complete_when_no_candidates_raises_external_service_error() -> None:
    client = _client(lambda _request: httpx.Response(200, json={"candidates": []}))

    with pytest.raises(ExternalServiceError):
        await client.complete(MESSAGES)
