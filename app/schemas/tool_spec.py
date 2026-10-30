from typing import Any

from pydantic import BaseModel


class ToolSpec(BaseModel):
    """One tool an agent may call. `name` is qualified as `<server>.<tool>`."""

    name: str
    server: str
    description: str
    input_schema: dict[str, Any]
