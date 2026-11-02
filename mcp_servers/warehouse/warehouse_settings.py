from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class WarehouseSettings(BaseSettings):
    """Settings for the warehouse server, read from `WAREHOUSE_*` env vars and `.env`."""

    model_config = SettingsConfigDict(
        env_prefix="WAREHOUSE_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    db_path: Path = Path("data/warehouse.db")
    csv_path: Path = Path("data/orders.csv")
    max_rows: int = 200
    # Rebuild the demo data each time the server starts, so "the last 24 hours" always has
    # orders in it. Off by default; `.env.example` turns it on for local demos.
    seed_on_startup: bool = False
