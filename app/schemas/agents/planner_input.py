from pydantic import BaseModel, Field

from app.schemas.tool_spec import ToolSpec


class PlannerInput(BaseModel):
    task: str = Field(min_length=1)
    tools: list[ToolSpec]
