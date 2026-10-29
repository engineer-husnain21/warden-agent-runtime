import logging
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.exceptions import WardenError
from app.core.logging import get_logger, get_request_id

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Turns WardenError into its HTTP status and any other exception into a safe 500."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except WardenError as error:
            level = logging.ERROR if error.status_code >= 500 else logging.WARNING
            logger.log(level, "%s: %s", error.error_code, error.message)
            return _error_response(
                error.status_code, error.error_code, error.message, error.details
            )
        except Exception:
            logger.exception("Unhandled error on %s %s", request.method, request.url.path)
            return _error_response(500, "internal_error", "Internal server error", {})


def _error_response(
    status_code: int, code: str, message: str, details: dict[str, Any]
) -> JSONResponse:
    body = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": get_request_id(),
        }
    }
    return JSONResponse(status_code=status_code, content=body)
