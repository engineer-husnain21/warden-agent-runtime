import asyncio
import re
from pathlib import Path

from app.core.exceptions import InvalidInputError, NotFoundError

_VALID_PROMPT_NAME = re.compile(r"^[a-z0-9_]+$")


class FilePromptLoader:
    """PromptLoader that reads `<name>.md` files from one directory and caches them."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory
        self._cache: dict[str, str] = {}

    async def load(self, name: str) -> str:
        if not _VALID_PROMPT_NAME.match(name):
            raise InvalidInputError(f"Invalid prompt name: {name!r}", details={"name": name})
        if name not in self._cache:
            path = self._directory / f"{name}.md"
            if not path.is_file():
                raise NotFoundError(f"Prompt {name} not found", details={"name": name})
            self._cache[name] = await asyncio.to_thread(path.read_text, encoding="utf-8")
        return self._cache[name]
