import json

from app.schemas.tool_result import ToolResult

MAX_RESULT_CHARS = 4000


def format_tool_result(result: ToolResult, max_chars: int = MAX_RESULT_CHARS) -> str:
    """Tool result as compact JSON text for a prompt, cut off at `max_chars`."""
    if not result.ok:
        return f"FAILED: {result.error}"
    text = json.dumps(result.content, ensure_ascii=False, default=str)
    if len(text) > max_chars:
        return f"{text[:max_chars]}... [cut off, {len(text)} characters in total]"
    return text
