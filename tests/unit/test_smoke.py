import importlib


def test_import_app_when_installed_succeeds() -> None:
    module = importlib.import_module("app")

    assert module.__name__ == "app"
