import pytest

from app.core.exceptions import (
    AgentOutputError,
    ExternalServiceError,
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
    WardenError,
)


def test_not_found_error_when_created_has_404_status() -> None:
    error = NotFoundError("Run 42 not found", details={"run_id": 42})

    assert error.status_code == 404
    assert error.error_code == "not_found"
    assert error.message == "Run 42 not found"
    assert error.details == {"run_id": 42}


def test_warden_error_when_no_details_defaults_to_empty_dict() -> None:
    assert WardenError("boom").details == {}


@pytest.mark.parametrize(
    ("error_class", "status_code"),
    [
        (PermissionDeniedError, 403),
        (InvalidInputError, 422),
        (ExternalServiceError, 502),
        (AgentOutputError, 502),
    ],
)
def test_subclass_when_created_is_warden_error_with_status(
    error_class: type[WardenError], status_code: int
) -> None:
    error = error_class("failed")

    assert isinstance(error, WardenError)
    assert error.status_code == status_code
