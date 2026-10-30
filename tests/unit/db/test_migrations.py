import sqlite3
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

import app.models  # noqa: F401  (registers all tables on Base.metadata)
from app.db.base import Base

PROJECT_ROOT = Path(__file__).resolve().parents[3]
APP_TABLES = {"agent_runs", "run_steps", "approvals", "audit_log_entries"}


def _alembic_config(db_path: Path) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_path.as_posix()}")
    config.attributes["configure_logging"] = False
    return config


def _table_names(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        return {row[0] for row in rows}


def test_alembic_upgrade_when_empty_db_succeeds(tmp_path: Path) -> None:
    db_path = tmp_path / "warden.db"

    command.upgrade(_alembic_config(db_path), "head")

    assert db_path.exists()
    assert "alembic_version" in _table_names(db_path)


def test_alembic_upgrade_when_applied_creates_all_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "warden.db"

    command.upgrade(_alembic_config(db_path), "head")

    assert _table_names(db_path) >= APP_TABLES


def test_alembic_downgrade_when_applied_drops_all_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "warden.db"
    config = _alembic_config(db_path)
    command.upgrade(config, "head")

    command.downgrade(config, "base")

    assert not APP_TABLES & _table_names(db_path)


def test_migrations_when_applied_match_models(tmp_path: Path) -> None:
    db_path = tmp_path / "warden.db"
    command.upgrade(_alembic_config(db_path), "head")

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()

    assert diff == []
