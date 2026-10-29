import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _alembic_config(db_path: Path) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_path.as_posix()}")
    config.attributes["configure_logging"] = False
    return config


def test_alembic_upgrade_when_empty_db_succeeds(tmp_path: Path) -> None:
    db_path = tmp_path / "warden.db"

    command.upgrade(_alembic_config(db_path), "head")

    assert db_path.exists()
    with sqlite3.connect(db_path) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
    assert "alembic_version" in tables
