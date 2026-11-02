from pydantic import BaseModel, Field


class CreateAgentRunRequest(BaseModel):
    task: str = Field(min_length=3, max_length=2000, description="What the agents should do.")
