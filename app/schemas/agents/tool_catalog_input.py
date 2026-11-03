from pydantic import BaseModel


class ToolCatalogInput(BaseModel):
    """No fields yet: every run sees every tool; permissions are checked per call later."""
