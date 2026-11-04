"""CLAUDE.md section 7: `.env.example` lists every variable that a settings class reads."""

import re
from pathlib import Path

import pytest
from pydantic_settings import BaseSettings

from app.core.config import Settings
from mcp_servers.github.github_settings import GitHubSettings
from mcp_servers.notifier.notifier_settings import NotifierSettings
from mcp_servers.warehouse.warehouse_settings import WarehouseSettings
from web.console_settings import ConsoleSettings

ENV_EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"


def _listed_variables() -> set[str]:
    return set(re.findall(r"^([A-Z][A-Z0-9_]*)=", ENV_EXAMPLE.read_text(encoding="utf-8"), re.M))


@pytest.mark.parametrize(
    "settings_class",
    [Settings, ConsoleSettings, GitHubSettings, NotifierSettings, WarehouseSettings],
)
def test_env_example_when_read_lists_every_settings_field(
    settings_class: type[BaseSettings],
) -> None:
    prefix = settings_class.model_config.get("env_prefix") or ""
    expected = {f"{prefix}{field}".upper() for field in settings_class.model_fields}

    assert expected - _listed_variables() == set()
