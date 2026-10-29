from fastapi import APIRouter

from app.schemas.health_response import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def get_health() -> HealthResponse:
    """Liveness check: the process is up and serving requests."""
    return HealthResponse()
