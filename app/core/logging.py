import logging
import sys
from contextvars import ContextVar
from typing import TextIO

LOG_FORMAT = "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"
NO_REQUEST_ID = "-"

_request_id_var: ContextVar[str] = ContextVar("request_id", default=NO_REQUEST_ID)


class RequestIdFilter(logging.Filter):
    """Adds the current request ID to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get()
        return True


def set_request_id(request_id: str) -> None:
    _request_id_var.set(request_id)


def get_request_id() -> str:
    return _request_id_var.get()


def configure_logging(level: str = "INFO", stream: TextIO | None = None) -> None:
    """Configure the root logger once at startup. Safe to call again (replaces handlers)."""
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Return the shared logger for a module. Use `get_logger(__name__)`."""
    return logging.getLogger(name)
