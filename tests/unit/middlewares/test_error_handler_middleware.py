from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from app.core.exceptions import NotFoundError
from app.middlewares.error_handler_middleware import ErrorHandlerMiddleware


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)

    @app.get("/missing")
    async def missing() -> None:
        raise NotFoundError("Run 7 not found", details={"run_id": 7})

    @app.get("/crash")
    async def crash() -> None:
        raise RuntimeError("secret internal detail")

    @app.get("/ok")
    async def ok() -> dict[str, str]:
        return {"status": "ok"}

    return app


async def _get(path: str) -> Response:
    transport = ASGITransport(app=_build_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


async def test_dispatch_when_warden_error_returns_json_error() -> None:
    response = await _get("/missing")

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert error["message"] == "Run 7 not found"
    assert error["details"] == {"run_id": 7}
    assert "request_id" in error


async def test_dispatch_when_unexpected_error_returns_500_without_internals() -> None:
    response = await _get("/crash")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "secret internal detail" not in response.text


async def test_dispatch_when_no_error_passes_response_through() -> None:
    response = await _get("/ok")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
