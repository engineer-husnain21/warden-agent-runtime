import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient, Response

from app.middlewares.api_key_auth_middleware import API_KEY_HEADER, ApiKeyAuthMiddleware
from app.middlewares.error_handler_middleware import ErrorHandlerMiddleware
from app.schemas.caller import Caller
from app.schemas.role import Role

API_KEYS = {
    "viewer-key": Caller(name="vera", role=Role.VIEWER),
    "admin-key": Caller(name="ada", role=Role.ADMIN),
}
EXEMPT_PATHS = ["/api/v1/health", "/docs", "/openapi.json"]


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(ApiKeyAuthMiddleware, api_keys=API_KEYS, exempt_paths=EXEMPT_PATHS)
    app.add_middleware(ErrorHandlerMiddleware)

    @app.get("/api/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/whoami")
    async def whoami(request: Request) -> dict[str, str]:
        caller: Caller = request.state.caller
        return {"name": caller.name, "role": caller.role.value}

    return app


async def _get(path: str, api_key: str | None = None) -> Response:
    headers = {API_KEY_HEADER: api_key} if api_key is not None else {}
    transport = ASGITransport(app=_build_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path, headers=headers)


async def test_dispatch_when_key_unknown_returns_401() -> None:
    response = await _get("/api/v1/whoami", api_key="wrong-key")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


async def test_dispatch_when_key_missing_returns_401() -> None:
    response = await _get("/api/v1/whoami")

    assert response.status_code == 401


async def test_dispatch_when_viewer_key_sets_role() -> None:
    response = await _get("/api/v1/whoami", api_key="viewer-key")

    assert response.status_code == 200
    assert response.json() == {"name": "vera", "role": "viewer"}


@pytest.mark.parametrize("path", EXEMPT_PATHS)
async def test_dispatch_when_exempt_path_without_key_passes(path: str) -> None:
    response = await _get(path)

    assert response.status_code == 200
