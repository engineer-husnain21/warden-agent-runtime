from typing import Any, ClassVar


class WardenError(Exception):
    """Base class for all expected errors. The error middleware maps it to an HTTP response."""

    status_code: ClassVar[int] = 500
    error_code: ClassVar[str] = "internal_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(WardenError):
    status_code = 404
    error_code = "not_found"


class PermissionDeniedError(WardenError):
    status_code = 403
    error_code = "permission_denied"


class InvalidInputError(WardenError):
    status_code = 422
    error_code = "invalid_input"


class ExternalServiceError(WardenError):
    """An outside API (LLM, MCP server, GitHub) failed or returned something unusable."""

    status_code = 502
    error_code = "external_service_error"


class ConfigurationError(WardenError):
    """A required setting is missing or invalid (e.g. no API key for the chosen LLM provider)."""

    status_code = 500
    error_code = "configuration_error"


class AgentOutputError(WardenError):
    """An agent could not turn the LLM reply into its Output model."""

    status_code = 502
    error_code = "agent_output_invalid"
