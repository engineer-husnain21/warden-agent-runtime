"""CLAUDE.md sections 1-4 as tests: calls only go downward and no layer is skipped."""

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP = PROJECT_ROOT / "app"

# Layer -> the app layers it may import (besides itself).
ALLOWED: dict[str, set[str]] = {
    "main": {"core", "middlewares", "routers"},
    "middlewares": {"core", "schemas"},
    "routers": {"core", "schemas", "services"},
    # Services build entities (models) to hand to repositories; they never reach clients.
    "services": {"core", "schemas", "orchestrators", "repositories", "models"},
    "orchestrators": {"core", "schemas", "agents", "policies"},
    "policies": {"schemas"},
    "agents": {"core", "schemas", "clients"},
    "clients": {"core", "schemas"},
    "repositories": {"core", "schemas", "db", "models"},
    "models": {"db", "schemas"},
    "db": {"core"},
    "schemas": set(),
    "core": {"schemas"},
}
# Composition roots wire every layer together; they are the only exceptions.
EXEMPT = {APP / "core" / "dependencies.py"}
EXEMPT_DIRS = {APP / "db" / "migrations"}
OUTSIDE_PACKAGES = {"mcp_servers", "web", "evals"}


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def _layer(path: Path) -> str:
    relative = path.relative_to(APP)
    return relative.parts[0] if len(relative.parts) > 1 else relative.stem


def _app_files() -> list[Path]:
    return [
        path
        for path in APP.rglob("*.py")
        if path not in EXEMPT and not any(folder in path.parents for folder in EXEMPT_DIRS)
    ]


def test_layers_when_imported_never_import_upward() -> None:
    violations = []
    for path in _app_files():
        layer = _layer(path)
        for name in _imports(path):
            parts = name.split(".")
            target = parts[1] if parts[0] == "app" and len(parts) > 1 else None
            upward = target not in (None, layer) and target not in ALLOWED.get(layer, set())
            if parts[0] in OUTSIDE_PACKAGES or upward:
                violations.append(f"{path.relative_to(PROJECT_ROOT)} imports {name}")

    assert violations == []


def test_services_when_imported_never_import_clients() -> None:
    services = (APP / "services").rglob("*.py")
    offenders = [
        f"{path.name} imports {name}"
        for path in services
        for name in _imports(path)
        if name.startswith("app.clients")
    ]

    assert offenders == []


def test_mcp_servers_and_web_when_imported_never_import_app() -> None:
    """MCP servers and the web console are separate programs: they never import `app`."""
    offenders = [
        f"{path.relative_to(PROJECT_ROOT)} imports {name}"
        for package in ("mcp_servers", "web")
        for path in (PROJECT_ROOT / package).rglob("*.py")
        for name in _imports(path)
        if name.split(".")[0] == "app"
    ]

    assert offenders == []


EVALS_MAY_IMPORT = ("app.main", "app.core", "app.schemas")


def test_evals_when_imported_use_only_app_entry_point_core_and_schemas() -> None:
    """Evals drive the app over HTTP, so they never reach into services, agents or repositories."""
    offenders = [
        f"{path.relative_to(PROJECT_ROOT)} imports {name}"
        for path in (PROJECT_ROOT / "evals").rglob("*.py")
        for name in _imports(path)
        if name.split(".")[0] == "app"
        and not any(
            name == allowed or name.startswith(f"{allowed}.") for allowed in EVALS_MAY_IMPORT
        )
    ]

    assert offenders == []
