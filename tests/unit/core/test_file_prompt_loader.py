from pathlib import Path

import pytest

from app.core.exceptions import InvalidInputError, NotFoundError
from app.core.file_prompt_loader import FilePromptLoader
from app.core.prompt_loader import PromptLoader


async def test_load_when_file_exists_returns_text(tmp_path: Path) -> None:
    (tmp_path / "planner_system.md").write_text("You are a planner.", encoding="utf-8")
    loader: PromptLoader = FilePromptLoader(tmp_path)

    assert await loader.load("planner_system") == "You are a planner."


async def test_load_when_file_missing_raises_not_found(tmp_path: Path) -> None:
    with pytest.raises(NotFoundError):
        await FilePromptLoader(tmp_path).load("missing_prompt")


@pytest.mark.parametrize("name", ["../secrets", "Planner", "planner.md", ""])
async def test_load_when_name_invalid_raises_invalid_input(tmp_path: Path, name: str) -> None:
    with pytest.raises(InvalidInputError):
        await FilePromptLoader(tmp_path).load(name)


async def test_load_when_called_twice_reads_file_once(tmp_path: Path) -> None:
    path = tmp_path / "reporter_system.md"
    path.write_text("v1", encoding="utf-8")
    loader = FilePromptLoader(tmp_path)
    await loader.load("reporter_system")
    path.write_text("v2", encoding="utf-8")

    assert await loader.load("reporter_system") == "v1"
