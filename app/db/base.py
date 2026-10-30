from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Enum
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all entities in `app/models/`."""


def utc_now() -> datetime:
    """Timezone-aware UTC timestamp for column defaults."""
    return datetime.now(UTC)


def str_enum_type(enum_class: type[StrEnum]) -> Enum:
    """Store a StrEnum as its plain string values (portable across SQLite and PostgreSQL)."""
    return Enum(
        enum_class,
        native_enum=False,
        length=30,
        values_callable=lambda members: [member.value for member in members],
    )
