import pytest

from app.core.dependencies import PROMPTS_DIR
from app.core.file_prompt_loader import FilePromptLoader
from app.schemas.tool_spec import ToolSpec


@pytest.fixture
def prompt_loader() -> FilePromptLoader:
    """The real prompt files, so tests also catch missing prompts or placeholders."""
    return FilePromptLoader(PROMPTS_DIR)


@pytest.fixture
def tool_specs() -> list[ToolSpec]:
    return [
        ToolSpec(
            name="warehouse.run_query",
            server="warehouse",
            description="Run one read-only SQL SELECT.",
            input_schema={"type": "object", "properties": {"sql": {"type": "string"}}},
        ),
        ToolSpec(
            name="github.create_issue",
            server="github",
            description="Open a new issue.",
            input_schema={
                "type": "object",
                "properties": {"title": {"type": "string"}, "body": {"type": "string"}},
            },
        ),
    ]
