import pytest

from app.clients.llm_client import LlmClient
from app.schemas.llm_message import LlmMessage
from tests.fakes.fake_llm_client import FakeLlmClient


async def test_fake_llm_client_when_called_returns_scripted_reply() -> None:
    client: LlmClient = FakeLlmClient(["first reply", "second"])

    response = await client.complete([LlmMessage(role="user", content="hello there")])

    assert response.text == "first reply"
    assert response.usage.input_tokens == 2
    assert response.usage.output_tokens == 2
    assert response.usage.total_tokens == 4


async def test_fake_llm_client_when_out_of_replies_fails_loudly() -> None:
    client = FakeLlmClient([])

    with pytest.raises(AssertionError):
        await client.complete([LlmMessage(role="user", content="hi")])
