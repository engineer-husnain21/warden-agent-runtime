from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.middlewares.request_id_middleware import REQUEST_ID_HEADER


async def test_get_health_when_app_running_returns_ok() -> None:
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers[REQUEST_ID_HEADER]


async def test_get_protected_path_when_no_key_returns_401_with_request_id() -> None:
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/agent-runs")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"
    assert response.headers[REQUEST_ID_HEADER]
