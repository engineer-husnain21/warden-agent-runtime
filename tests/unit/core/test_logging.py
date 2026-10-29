import contextvars
import io
import logging
from collections.abc import Iterator

import pytest

from app.core.logging import NO_REQUEST_ID, configure_logging, get_logger, set_request_id


@pytest.fixture
def log_stream() -> Iterator[io.StringIO]:
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    stream = io.StringIO()
    configure_logging("INFO", stream=stream)
    yield stream
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)


def test_get_logger_when_request_id_set_includes_it(log_stream: io.StringIO) -> None:
    def log_in_request() -> None:
        set_request_id("req-123")
        get_logger("warden.test").info("hello")

    contextvars.copy_context().run(log_in_request)

    assert "[req-123] warden.test: hello" in log_stream.getvalue()


def test_get_logger_when_no_request_id_uses_placeholder(log_stream: io.StringIO) -> None:
    contextvars.copy_context().run(get_logger("warden.test").info, "hello")

    assert f"[{NO_REQUEST_ID}]" in log_stream.getvalue()


def test_configure_logging_when_level_warning_drops_info(log_stream: io.StringIO) -> None:
    configure_logging("WARNING", stream=log_stream)

    get_logger("warden.test").info("hidden")

    assert "hidden" not in log_stream.getvalue()
