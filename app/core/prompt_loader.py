from typing import Protocol


class PromptLoader(Protocol):
    """Loads prompt text by name (e.g. `planner_system` → `prompts/planner_system.md`)."""

    async def load(self, name: str) -> str: ...
