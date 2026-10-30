import asyncio
import random
from collections.abc import Awaitable, Callable

import httpx

from app.core.logging import get_logger

RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})

logger = get_logger(__name__)


def is_retryable(error: Exception) -> bool:
    """Rate limits, server errors and network problems are worth retrying; nothing else is."""
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code in RETRYABLE_STATUS_CODES
    return isinstance(error, httpx.TransportError)


async def retry_with_backoff[T](
    operation: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 4,
    base_delay: float = 0.5,
    max_delay: float = 20.0,
    jitter: bool = True,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """Run `operation`, retrying retryable errors with exponential backoff.

    A `Retry-After` header (seconds) from the server wins when it asks for a longer wait.
    The last error is re-raised once `max_attempts` is reached.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()
        except Exception as error:
            if attempt == max_attempts or not is_retryable(error):
                raise
            delay = _next_delay(error, attempt, base_delay, max_delay, jitter)
            logger.warning(
                "Retryable error (attempt %d/%d), waiting %.2fs: %s",
                attempt,
                max_attempts,
                delay,
                error,
            )
            await sleep(delay)
    raise AssertionError("unreachable")  # pragma: no cover


def _next_delay(
    error: Exception, attempt: int, base_delay: float, max_delay: float, jitter: bool
) -> float:
    delay = min(max_delay, base_delay * 2.0 ** (attempt - 1))
    if jitter:
        delay += random.uniform(0, delay * 0.1)
    retry_after = _retry_after_seconds(error)
    if retry_after is not None:
        delay = max(delay, min(retry_after, max_delay))
    return delay


def _retry_after_seconds(error: Exception) -> float | None:
    if not isinstance(error, httpx.HTTPStatusError):
        return None
    header = error.response.headers.get("Retry-After")
    try:
        return float(header) if header is not None else None
    except ValueError:
        return None
