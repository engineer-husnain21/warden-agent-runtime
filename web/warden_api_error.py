class WardenApiError(Exception):
    """The API answered with an error; `message` is the API's own error message."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"{status_code}: {message}")
        self.status_code = status_code
        self.message = message
