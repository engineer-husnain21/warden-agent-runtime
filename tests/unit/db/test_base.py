from enum import StrEnum

from app.db.base import str_enum_type, utc_now


class _Color(StrEnum):
    RED = "red"
    DARK_BLUE = "dark-blue"


def test_utc_now_when_called_returns_timezone_aware_utc() -> None:
    now = utc_now()

    assert now.utcoffset() is not None
    assert now.utcoffset().total_seconds() == 0  # type: ignore[union-attr]


def test_str_enum_type_when_built_stores_values_not_names() -> None:
    column_type = str_enum_type(_Color)

    assert column_type.enums == ["red", "dark-blue"]
    assert column_type.native_enum is False
