import logging

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.logging import get_request_id
from app.middlewares.request_id_middleware import REQUEST_ID_HEADER, RequestIdMiddleware


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"request_id": get_request_id()}

    return app


async def _get(headers: dict[str, str] | None = None) -> tuple[str, str]:
    transport = ASGITransport(app=_build_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ping", headers=headers)
    return response.headers[REQUEST_ID_HEADER], response.json()["request_id"]


async def test_dispatch_when_no_header_sets_x_request_id() -> None:
    header_id, seen_by_endpoint = await _get()

    assert len(header_id) == 32
    assert seen_by_endpoint == header_id


async def test_dispatch_when_valid_header_reuses_it() -> None:
    header_id, seen_by_endpoint = await _get({REQUEST_ID_HEADER: "client-abc.1"})

    assert header_id == "client-abc.1"
    assert seen_by_endpoint == "client-abc.1"


async def test_dispatch_when_header_invalid_generates_new_id() -> None:
    header_id, _ = await _get({REQUEST_ID_HEADER: "bad id\nwith newline"})

    assert header_id != "bad id\nwith newline"
    assert len(header_id) == 32


async def test_dispatch_when_request_done_writes_access_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="app.middlewares.request_id_middleware"):
        await _get()

    assert any("GET /ping 200" in record.getMessage() for record in caplog.records)
