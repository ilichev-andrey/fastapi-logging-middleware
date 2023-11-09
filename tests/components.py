from starlette.responses import Response

JSON_MEDIA_TYPE = 'application/json'


class Logger:
    """A test-only class that simulates logging."""

    def log(self, *args, **kwargs) -> None:
        """Function simulating logging (mock object will be created)."""


class ResponseGetter:
    """A test-only class that will produce a test-defined response."""

    def get(self) -> Response:
        """Give a specific response."""
