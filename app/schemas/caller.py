from pydantic import BaseModel

from app.schemas.role import Role


class Caller(BaseModel):
    """Who is making the request, resolved from the API key by ApiKeyAuthMiddleware."""

    name: str
    role: Role
