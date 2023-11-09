from dataclasses import dataclass, field, asdict
from typing import Literal, Optional, Dict, Type, Callable, Any, AbstractSet, Hashable

from starlette.concurrency import iterate_in_threadpool
from starlette.datastructures import Address, Headers, URL, QueryParams, MutableHeaders
from starlette.requests import Request
from starlette.responses import HTMLResponse, PlainTextResponse, JSONResponse, Response, StreamingResponse

from fastapi_logging_middleware.utils import orjson_dumps

MaskedNamesType = AbstractSet[str]
DEFAULT_MASKED_NAMES: MaskedNamesType = frozenset(('authorization', 'token'))


def convert_to_str(value: Any) -> str:
    """Convert any value to a string."""
    return str(value)


def convert_headers_to_dict(headers: Headers) -> Dict[str, str]:
    """Convert an object `starlette.Headers` to a string."""
    return dict(headers.items())


def convert_address_to_dict(address: Address) -> Dict[str, Any]:
    """Convert an object `starlette.Address` to a string."""
    return address._asdict()  # noqa: WPS437


@dataclass
class BaseInfo:
    """Base class for storing information about HTTP objects."""

    class Config:
        """Additional configuration of various features."""

        masked_value: str = 'MASKED'
        dumpers: Dict[Type[Hashable], Callable[..., Any]] = {
            URL: convert_to_str,
            QueryParams: convert_to_str,
            Headers: convert_headers_to_dict,
            Address: convert_address_to_dict,
        }

    def as_dict(
            self,
            is_mask_private_data: bool = True,
            masked_names: MaskedNamesType = DEFAULT_MASKED_NAMES,
            exclude_none: bool = True
    ) -> Dict[str, Any]:
        """Convert this object to a dictionary."""
        data = asdict(self)
        if exclude_none:
            data = {key: value for key, value in data.items() if value is not None}
        for key, value in data.items():
            if is_mask_private_data:
                value = self._mask_private_data(data=value, masked_names=masked_names)
            for dumper_type, func in self.Config.dumpers.items():
                if isinstance(value, dumper_type):
                    data[key] = func(value)
        return data

    def as_json(
            self,
            is_mask_private_data: bool = True,
            masked_names: MaskedNamesType = DEFAULT_MASKED_NAMES,
            exclude_none: bool = True
    ) -> str:
        """Convert this object to a JSON string."""
        return orjson_dumps(self.as_dict(
            is_mask_private_data=is_mask_private_data,
            masked_names=masked_names,
            exclude_none=exclude_none
        ))

    @classmethod
    def _mask_private_data(cls, data: Any, masked_names: MaskedNamesType) -> Any:
        if isinstance(data, QueryParams):
            return cls._mask_private_params(params=data, masked_names=masked_names)
        if isinstance(data, Headers):
            return cls._mask_private_headers(headers=data, masked_names=masked_names)
        return data

    @classmethod
    def _mask_private_params(cls, params: QueryParams, masked_names: MaskedNamesType) -> QueryParams:
        new_params = []
        for (key, value) in params.multi_items():
            normalize_key = str(key).lower()
            if normalize_key in masked_names:
                value = cls.Config.masked_value  # noqa: WPS440
            new_params.append((key, value))
        return QueryParams(new_params)

    @classmethod
    def _mask_private_headers(cls, headers: Headers, masked_names: MaskedNamesType) -> MutableHeaders:
        headers = headers.mutablecopy()
        for name in masked_names:
            if headers.get(name) is not None:
                headers[name] = cls.Config.masked_value
        return headers


@dataclass
class RequestInfo(BaseInfo):
    """Information about the incoming request."""

    type: Literal['Request'] = field(default='Request', init=False)
    method: str
    path: str
    query_params: QueryParams
    headers: Headers
    client_address: Optional[Address] = None
    body: Optional[str] = None

    @classmethod
    async def from_starlette_request(cls, request: Request, include_body: bool) -> 'RequestInfo':
        """Convert a request object (starlette) to a serializable object (dataclass)."""
        body = None
        if include_body:
            body = await request.body()
            body = str(body)
        return RequestInfo(
            method=request.method,
            path=request.url.path,
            query_params=request.query_params,
            headers=request.headers,
            client_address=request.client,
            body=body
        )

    def mask_private_data(self, masked_names: MaskedNamesType = DEFAULT_MASKED_NAMES) -> 'RequestInfo':
        """Copy this object with masked private data."""
        query_params = self._mask_private_params(params=self.query_params, masked_names=masked_names)
        headers = self._mask_private_headers(headers=self.headers, masked_names=masked_names)
        return RequestInfo(
            method=self.method,
            path=self.path,
            query_params=query_params,
            headers=Headers(raw=headers.raw),
            client_address=self.client_address,
            body=self.body
        )


@dataclass
class EndpointInfo(BaseInfo):
    """Information about the endpoint."""

    method: str
    path: str


@dataclass
class ResponseInfo(BaseInfo):
    """Information about the outgoing response."""

    type: Literal['Response'] = field(default='Response', init=False)
    status_code: int
    headers: MutableHeaders
    request: Optional[EndpointInfo] = None
    body: Optional[str] = None

    @classmethod
    async def from_starlette_response(
            cls,
            response: Response,
            include_body: bool,
            request: Optional[Request] = None,
            request_info: Optional[EndpointInfo] = None
    ) -> 'ResponseInfo':
        """Convert a request object (starlette) to a serializable object (dataclass)."""
        if request is not None:
            request_info = EndpointInfo(method=request.method, path=request.url.path)

        body = None
        if include_body:
            body = await _get_response_body(response=response)
        return ResponseInfo(
            status_code=response.status_code,
            headers=response.headers,
            request=request_info,
            body=body
        )

    def mask_private_data(self, masked_names: MaskedNamesType = DEFAULT_MASKED_NAMES) -> 'ResponseInfo':
        """Copy this object with masked private data."""
        headers = self._mask_private_headers(headers=self.headers, masked_names=masked_names)
        return ResponseInfo(
            status_code=self.status_code,
            headers=headers,
            request=self.request,
            body=self.body
        )


async def _get_response_body(response: Response) -> Optional[str]:
    response_body = None
    if isinstance(response, StreamingResponse):
        # Consuming FastAPI response and grabbing body here
        response_body_chunks = [chunk async for chunk in response.body_iterator]
        # Repairing FastAPI response
        response.body_iterator = iterate_in_threadpool(iter(response_body_chunks))
        response_body = b''.join(response_body_chunks)
    elif isinstance(response, (HTMLResponse, PlainTextResponse, JSONResponse)):
        response_body = response.body

    if response_body is not None:
        return str(response_body)
    return None
