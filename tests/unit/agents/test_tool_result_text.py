from app.agents.tool_result_text import format_tool_result
from app.schemas.tool_result import ToolResult


def test_format_tool_result_when_long_cuts_off_with_note() -> None:
    result = ToolResult(tool="warehouse.run_query", ok=True, content={"text": "x" * 100})

    text = format_tool_result(result, max_chars=20)

    assert text.startswith('{"text": "xxxxxxxxx')
    assert "cut off" in text


def test_format_tool_result_when_failed_shows_error() -> None:
    result = ToolResult(tool="github.create_issue", ok=False, error="401")

    assert format_tool_result(result) == "FAILED: 401"
