"""A small app with the real middlewares, the given routers and service overrides."""

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient

from app.middlewares.api_key_auth_middleware import API_KEY_HEADER, ApiKeyAuthMiddleware
from app.middlewares.error_handler_middleware import ErrorHandlerMiddleware
from app.schemas.caller import Caller
from app.schemas.role import Role

API_KEYS = {
    "viewer-key": Caller(name="vera", role=Role.VIEWER),
    "operator-key": Caller(name="oscar", role=Role.OPERATOR),
    "admin-key": Caller(name="ada", role=Role.ADMIN),
}


def build_client(routers: list[APIRouter], overrides: Mapping[Any, Any], key: str) -> AsyncClient:
    """`overrides` maps a dependency function (e.g. get_approval_service) to a factory."""
    app = FastAPI()
    app.add_middleware(ApiKeyAuthMiddleware, api_keys=API_KEYS, exempt_paths=[])
    app.add_middleware(ErrorHandlerMiddleware)
    for router in routers:
        app.include_router(router, prefix="/api/v1")
    app.dependency_overrides.update(overrides)
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={API_KEY_HEADER: key},
    )
