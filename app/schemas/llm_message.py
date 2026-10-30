from typing import Literal

from pydantic import BaseModel


class LlmMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str
