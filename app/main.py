from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.dependencies import get_engine, get_http_client
from app.core.logging import configure_logging
from app.middlewares.error_handler_middleware import ErrorHandlerMiddleware
from app.middlewares.request_id_middleware import RequestIdMiddleware
from app.routers import health_router

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    await get_http_client().aclose()
    await get_engine().dispose()


def create_app() -> FastAPI:
    configure_logging(get_settings().log_level)

    app = FastAPI(title="Warden Agent Runtime", version="0.1.0", lifespan=lifespan)

    # The last middleware added runs first: RequestId wraps ErrorHandler,
    # so error responses still carry X-Request-ID.
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RequestIdMiddleware)

    app.include_router(health_router.router, prefix=API_PREFIX)
    return app


app = create_app()
