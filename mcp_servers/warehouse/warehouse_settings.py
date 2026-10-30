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
