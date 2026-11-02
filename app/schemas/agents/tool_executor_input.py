from pydantic import BaseModel

from app.schemas.tool_call import ToolCall


class ToolExecutorInput(BaseModel):
    call: ToolCall
