from abc import abstractmethod
from typing import Callable, Optional

from starlette.requests import Request
from starlette.responses import Response

from fastapi_logging_middleware.http_exporter import RequestInfo, ResponseInfo
from fastapi_logging_middleware.utils import get_logger


class BaseHandler:
    """."""

    _include_body: bool
    _include_form: bool

    def __init__(self, include_body: bool = False, include_form: bool = False) -> None:
        """
        .

        Args:
            include_body:
            include_form:
        """

        self._include_body = include_body
        self._include_form = include_form

    @abstractmethod
    async def save_request_to_storage(self, request: Request) -> None:
        """."""

    @abstractmethod
    async def save_response_to_storage(self, request: Request, response: Response) -> None:
        """."""


LoggingFuncType = Callable[[str], None]
LoggingFuncFactory = Callable[[], LoggingFuncType]


class LoggingHandler(BaseHandler):
    """."""

    _logging_func_factory: LoggingFuncFactory

    def __init__(
            self,
            include_body: bool = False,
            include_form: bool = False,
            logging_func: Optional[LoggingFuncType] = None,
            logging_func_factory: Optional[LoggingFuncFactory] = None
    ):
        """
        .

        Args:
            include_body:
            include_form:
            logging_func:
            logging_func_factory:
        """
        super().__init__(include_body=include_body, include_form=include_form)

        if logging_func_factory is None:
            logger = get_logger()
            logging_func_factory = lambda: logger.info  # noqa: E731
        if logging_func is not None:
            logging_func_factory = lambda: logging_func  # noqa: E731

        self._logging_func_factory = logging_func_factory

    async def save_request_to_storage(self, request: Request) -> None:
        """."""
        request_info = await RequestInfo.from_starlette_request(
            request=request,
            include_body=self._include_body,
            include_form=self._include_form
        )
        self._logging_func_factory()(request_info.as_json())

    async def save_response_to_storage(self, request: Request, response: Response) -> None:
        """."""
        response_info = await ResponseInfo.from_starlette_response(
            request=request,
            response=response,
            include_body=self._include_body
        )
        self._logging_func_factory()(response_info.as_json())
