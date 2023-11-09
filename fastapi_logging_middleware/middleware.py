import asyncio
from typing import Sequence, Callable, Coroutine, Any, Tuple, Optional

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.base import RequestResponseEndpoint, BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute

from fastapi_logging_middleware import dependencies
from fastapi_logging_middleware.handlers import BaseHandler, LoggingHandler


class LoggingMiddleware:

    _handlers: Sequence[BaseHandler]

    def __init__(self, handlers: Optional[Sequence[BaseHandler]] = None) -> None:
        """
        .

        Args:
            handlers:
        """
        if not handlers:
            handlers = (LoggingHandler(),)

        self._handlers = handlers

    def register(self, app: FastAPI) -> None:
        self._add_dependencies(app=app)
        self._add_middleware(app=app)

    def _add_dependencies(self, app: FastAPI) -> None:
        for route in app.routes:
            for handler in self._handlers:
                self._add_dependency_to_route(route=route, handler=handler)

    @classmethod
    def _add_dependency_to_route(cls, route: BaseRoute, handler: BaseHandler) -> None:
        if isinstance(route, APIRoute):
            dependencies.add_dependency(route=route, dependency=handler.save_request_to_storage)
        else:
            pass  # TODO add

    def _add_middleware(self, app: FastAPI) -> None:
        middleware = self._create_middleware()
        app.add_middleware(BaseHTTPMiddleware, dispatch=middleware)

    def _create_middleware(self) -> Callable[[Request, RequestResponseEndpoint], Coroutine[Any, Any, Response]]:

        async def _middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
            response = await call_next(request)
            await self._handle_response(request=request, response=response)
            return response

        return _middleware

    async def _handle_response(self, request: Request, response: Response) -> None:
        tasks = (
            handler.save_response_to_storage(request=request, response=response)
            for handler in self._handlers
        )
        await asyncio.gather(*tasks, return_exceptions=True)
