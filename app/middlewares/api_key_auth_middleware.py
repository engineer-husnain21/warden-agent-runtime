import hmac
from collections.abc import Iterable, Mapping

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.exceptions import AuthenticationError
from app.schemas.caller import Caller

API_KEY_HEADER = "X-API-Key"


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """Resolves `X-API-Key` to a Caller on `request.state.caller`; unknown keys get 401.

    Paths in `exempt_paths` (health, docs) are served without a key.
    """

    def __init__(
        self, app: ASGIApp, api_keys: Mapping[str, Caller], exempt_paths: Iterable[str]
    ) -> None:
        super().__init__(app)
        self._api_keys = dict(api_keys)
        self._exempt_paths = frozenset(exempt_paths)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self._exempt_paths:
            return await call_next(request)

        caller = self._find_caller(request.headers.get(API_KEY_HEADER, ""))
        if caller is None:
            raise AuthenticationError("Missing or invalid API key")
        request.state.caller = caller
        return await call_next(request)

    def _find_caller(self, presented_key: str) -> Caller | None:
        if not presented_key:
            return None
        found: Caller | None = None
        # Compare against every key in constant time, so timing does not reveal valid keys.
        for key, caller in self._api_keys.items():
            if hmac.compare_digest(key.encode(), presented_key.encode()):
                found = caller
        return found
