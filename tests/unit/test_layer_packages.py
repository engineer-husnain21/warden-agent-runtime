import importlib

import pytest

LAYERS = [
    "core",
    "middlewares",
    "routers",
    "schemas",
    "services",
    "orchestrators",
    "agents",
    "prompts",
    "clients",
    "repositories",
    "models",
    "db",
]


@pytest.mark.parametrize("layer", LAYERS)
def test_layer_packages_when_imported_exist(layer: str) -> None:
    module = importlib.import_module(f"app.{layer}")

    assert module.__doc__
