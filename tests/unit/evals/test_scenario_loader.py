from pathlib import Path

import pytest

from app.core.exceptions import InvalidInputError
from app.schemas.role import Role
from evals.scenario_loader import load_scenarios

VALID = """
id: warehouse_count_failed
description: Counts failed orders
task: How many orders failed in the last 24 hours?
role: viewer
expect:
  tools: [warehouse.run_query]
  report_contains: ["35"]
"""


def _write(directory: Path, name: str, text: str) -> None:
    (directory / name).write_text(text, encoding="utf-8")


def test_load_scenarios_when_valid_parses_defaults(tmp_path: Path) -> None:
    _write(tmp_path, "warehouse_count_failed.yaml", VALID)

    [scenario] = load_scenarios(tmp_path)

    assert scenario.role is Role.VIEWER
    assert scenario.approval == "none"
    assert scenario.expect.status == "completed"
    assert "warehouse.describe_table" in scenario.expect.allowed_extra_tools


def test_load_scenarios_when_yaml_invalid_raises(tmp_path: Path) -> None:
    _write(tmp_path, "broken.yaml", "id: [unclosed")

    with pytest.raises(InvalidInputError, match=r"broken\.yaml"):
        load_scenarios(tmp_path)


def test_load_scenarios_when_field_unknown_raises(tmp_path: Path) -> None:
    _write(tmp_path, "typo.yaml", VALID + "aproval: approve\n")

    with pytest.raises(InvalidInputError, match=r"typo\.yaml"):
        load_scenarios(tmp_path)


def test_load_scenarios_when_no_expected_tools_raises(tmp_path: Path) -> None:
    _write(tmp_path, "no_tools.yaml", VALID.replace("[warehouse.run_query]", "[]"))

    with pytest.raises(InvalidInputError):
        load_scenarios(tmp_path)


def test_load_scenarios_when_ids_repeat_raises(tmp_path: Path) -> None:
    _write(tmp_path, "a.yaml", VALID)
    _write(tmp_path, "b.yaml", VALID)

    with pytest.raises(InvalidInputError, match="Duplicate scenario id"):
        load_scenarios(tmp_path)
