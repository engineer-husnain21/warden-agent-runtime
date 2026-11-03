from pathlib import Path

import yaml
from pydantic import ValidationError

from app.core.exceptions import InvalidInputError
from evals.scenario import Scenario

SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"


def load_scenarios(directory: Path = SCENARIOS_DIR) -> list[Scenario]:
    """Load every `*.yaml` file in `directory` (one scenario each), sorted by file name.

    Raises InvalidInputError naming the file when one is not valid YAML, does not match the
    Scenario schema, or reuses another scenario's id.
    """
    scenarios: list[Scenario] = []
    seen: dict[str, Path] = {}
    for path in sorted(directory.glob("*.yaml")):
        scenario = _load_file(path)
        if scenario.id in seen:
            raise InvalidInputError(
                f"Duplicate scenario id '{scenario.id}' in {path.name} and {seen[scenario.id].name}"
            )
        seen[scenario.id] = path
        scenarios.append(scenario)
    return scenarios


def _load_file(path: Path) -> Scenario:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return Scenario.model_validate(data)
    except (yaml.YAMLError, ValidationError) as error:
        raise InvalidInputError(
            f"Invalid scenario file {path.name}: {error}", details={"file": path.name}
        ) from error
