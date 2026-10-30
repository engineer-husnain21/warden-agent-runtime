"""Dependency wiring. Concrete classes are built here and injected with FastAPI `Depends`."""

import os
import sys
from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path

import httpx
from mcp import StdioServerParameters
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.clients.gemini_llm_client import GeminiLlmClient
from app.clients.groq_llm_client import GroqLlmClient
from app.clients.llm_client import LlmClient
from app.clients.mcp_tool_client import McpToolClient
from app.clients.tool_client import ToolClient
from app.core.config import get_settings
from app.core.exceptions import ConfigurationError
from app.core.file_prompt_loader import FilePromptLoader
from app.core.prompt_loader import PromptLoader
from app.db.session import build_engine, build_session_factory, get_session

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = PROJECT_ROOT / "app" / "prompts"


@lru_cache
def get_engine() -> AsyncEngine:
    return build_engine(get_settings().database_url)


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return build_session_factory(get_engine())


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async for session in get_session(get_session_factory()):
        yield session


@lru_cache
def get_http_client() -> httpx.AsyncClient:
    """One shared HTTP connection pool for all outside APIs; closed in the app lifespan."""
    return httpx.AsyncClient(timeout=get_settings().llm_timeout_seconds)


@lru_cache
def get_llm_client() -> LlmClient:
    settings = get_settings()
    if settings.llm_provider == "gemini":
        return GeminiLlmClient(
            api_key=_require_key(settings.gemini_api_key, "GEMINI_API_KEY"),
            model=settings.gemini_model,
            base_url=settings.gemini_base_url,
            input_price_per_mtok=settings.gemini_input_price_per_mtok,
            output_price_per_mtok=settings.gemini_output_price_per_mtok,
            http_client=get_http_client(),
            max_attempts=settings.llm_max_attempts,
        )
    return GroqLlmClient(
        api_key=_require_key(settings.groq_api_key, "GROQ_API_KEY"),
        model=settings.groq_model,
        base_url=settings.groq_base_url,
        input_price_per_mtok=settings.groq_input_price_per_mtok,
        output_price_per_mtok=settings.groq_output_price_per_mtok,
        http_client=get_http_client(),
        max_attempts=settings.llm_max_attempts,
    )


@lru_cache
def get_prompt_loader() -> PromptLoader:
    return FilePromptLoader(PROMPTS_DIR)


@lru_cache
def get_tool_client() -> ToolClient:
    """MCP servers run as child processes of this app; connected and closed in the lifespan."""
    settings = get_settings()
    servers = {
        name: StdioServerParameters(
            command=sys.executable,
            args=["-m", module],
            env=dict(os.environ),
            cwd=str(PROJECT_ROOT),
        )
        for name, module in settings.mcp_server_modules.items()
    }
    return McpToolClient(servers, timeout_seconds=settings.mcp_tool_timeout_seconds)


def _require_key(secret: SecretStr | None, env_name: str) -> str:
    value = secret.get_secret_value() if secret is not None else ""
    if not value:
        raise ConfigurationError(f"{env_name} is not set", details={"setting": env_name})
    return value
