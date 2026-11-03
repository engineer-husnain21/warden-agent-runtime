"""An isolated, in-process Warden for the eval suite.

Every database lives in a scratch directory, GitHub is always dry-run, and the API keys are
generated for this process only, so an eval never touches local data, `.env` keys or GitHub.
The LLM is real: its provider and key still come from the environment / `.env`.
"""

import json
import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from alembic import command
from alembic.config import Config

from app.core.config import get_settings
from app.schemas.role import Role

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_BASE_URL = "http://warden.eval/api/v1"
# Groq's per-minute token limit is hit often during a suite; wait it out instead of failing.
LLM_MAX_ATTEMPTS = 8


def prepare_environment(work_dir: Path) -> dict[Role, str]:
    """Point every setting at `work_dir`, create the schema and return one API key per role.

    Call before the event loop starts: Alembic runs its own loop. MCP servers inherit these
    variables because the app starts them with the current environment.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    keys = {role: f"eval-{role.value}-{secrets.token_hex(8)}" for role in Role}
    database_url = _sqlite_url(work_dir / "warden.db")
    callers = {
        key: {"name": f"eval-{role.value}", "role": role.value} for role, key in keys.items()
    }
    os.environ.update(
        {
            "DATABASE_URL": database_url,
            "CHECKPOINT_DATABASE_URL": _sqlite_url(work_dir / "checkpoints.db"),
            "WAREHOUSE_DB_PATH": str(work_dir / "warehouse.db"),
            "WAREHOUSE_SEED_ON_STARTUP": "true",
            "NOTIFIER_DB_PATH": str(work_dir / "notifier.db"),
            "GITHUB_MODE": "dry-run",
            "API_KEYS": json.dumps(callers),
            "LLM_MAX_ATTEMPTS": str(LLM_MAX_ATTEMPTS),
        }
    )
    get_settings.cache_clear()
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["configure_logging"] = False
    command.upgrade(config, "head")
    return keys


@asynccontextmanager
async def eval_client() -> AsyncIterator[httpx.AsyncClient]:
    """The real app with its lifespan (MCP servers, checkpoints), reached without a socket."""
    from app.main import create_app  # imported late: the app reads settings when imported

    app = create_app()
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url=API_BASE_URL, timeout=60.0
        ) as client:
            yield client


def _sqlite_url(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path.resolve().as_posix()}"
