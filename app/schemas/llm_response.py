from pydantic import BaseModel

from app.schemas.llm_usage import LlmUsage


class LlmResponse(BaseModel):
    text: str
    usage: LlmUsage
