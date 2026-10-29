import asyncio

from alembic import context
from sqlalchemy.engine import Connection

import app.models  # noqa: F401  (registers entities on Base.metadata)
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import build_engine

config = context.config
settings = get_settings()

# Tests run migrations in-process and set this to False to keep their own logging setup.
if config.attributes.get("configure_logging", True):
    configure_logging(settings.log_level)

database_url = config.get_main_option("sqlalchemy.url") or settings.database_url
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_migrations(connection: Connection) -> None:
    # render_as_batch lets SQLite handle ALTER TABLE through table copies.
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = build_engine(database_url)
    async with engine.connect() as connection:
        await connection.run_sync(_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
