from collections.abc import Awaitable, Callable

import httpx
import pytest

from app.clients.backoff import retry_with_backoff


def _status_error(status_code: int, headers: dict[str, str] | None = None) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://llm.test/v1/chat")
    response = httpx.Response(status_code, headers=headers, request=request)
    return httpx.HTTPStatusError("error", request=request, response=response)


def _scripted(outcomes: list[Exception | str]) -> tuple[Callable[[], Awaitable[str]], list[int]]:
    calls: list[int] = []

    async def operation() -> str:
        calls.append(1)
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return operation, calls


class _RecordingSleep:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


async def test_retry_with_backoff_when_429_then_ok_retries_once() -> None:
    operation, calls = _scripted([_status_error(429), "ok"])
    sleep = _RecordingSleep()

    result = await retry_with_backoff(operation, base_delay=0.5, jitter=False, sleep=sleep)

    assert result == "ok"
    assert len(calls) == 2
    assert sleep.delays == [0.5]


async def test_retry_with_backoff_when_always_failing_doubles_delay_then_raises() -> None:
    operation, calls = _scripted([_status_error(503)] * 3)
    sleep = _RecordingSleep()

    with pytest.raises(httpx.HTTPStatusError):
        await retry_with_backoff(operation, max_attempts=3, jitter=False, sleep=sleep)

    assert len(calls) == 3
    assert sleep.delays == [0.5, 1.0]


async def test_retry_with_backoff_when_client_error_raises_immediately() -> None:
    operation, calls = _scripted([_status_error(401)])
    sleep = _RecordingSleep()

    with pytest.raises(httpx.HTTPStatusError):
        await retry_with_backoff(operation, sleep=sleep)

    assert len(calls) == 1
    assert sleep.delays == []


async def test_retry_with_backoff_when_retry_after_header_waits_that_long() -> None:
    operation, _ = _scripted([_status_error(429, {"Retry-After": "7"}), "ok"])
    sleep = _RecordingSleep()

    await retry_with_backoff(operation, jitter=False, sleep=sleep)

    assert sleep.delays == [7.0]


async def test_retry_with_backoff_when_network_error_retries() -> None:
    operation, calls = _scripted([httpx.ConnectError("refused"), "ok"])

    result = await retry_with_backoff(operation, jitter=False, sleep=_RecordingSleep())

    assert result == "ok"
    assert len(calls) == 2
