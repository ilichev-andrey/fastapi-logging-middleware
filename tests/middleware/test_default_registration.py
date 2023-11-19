from typing import TYPE_CHECKING, Dict, Iterable
from unittest.mock import patch, Mock

import pytest
from orjson import orjson
from starlette import status
from starlette.responses import Response
from starlette.testclient import TestClient

from fastapi_logging_middleware import LoggingMiddleware
from tests.components import JSON_MEDIA_TYPE
from tests.middleware.default_registration_components import app, response_getter

if TYPE_CHECKING:
    from httpx._types import RequestContent, QueryParamTypes, HeaderTypes

_REQUEST_PARAMS = {
    'param1': 'param_value1',
    'param2': 'param_value2',
    'param_list': ['param_list_item1', 'param_list_item2'],
    'token': 'some_token_in_params',
    'authorization': 'some_authorization_in_params',
}
_EXPECTED_REQUEST_PARAMS = (
    'param1=param_value1&'
    'param2=param_value2&'
    'param_list=param_list_item1&'
    'param_list=param_list_item2&'
    'token=MASKED&'
    'authorization=MASKED'
)

_REQUEST_HEADERS = {
    'header1': 'header_value1',
    'header2': 'header_value2',
    'token': 'some_token_in_headers',
    'authorization': 'some_authorization_in_headers',
}
_EXPECTED_REQUEST_HEADERS = {
    **_REQUEST_HEADERS,
    'host': 'test',
    'accept': '*/*',
    'accept-encoding': 'gzip, deflate',
    'connection': 'keep-alive',
    'user-agent': 'testclient',
    'token': 'MASKED',
    'authorization': 'MASKED',
}

_REQUEST_BODY = b'{"request_body": "ok"}'
_REQUEST_BODY_LEN = len(_REQUEST_BODY)
_RESPONSE_BODY = b'{"response_body": "ok"}'
_RESPONSE_BODY_LEN = len(_RESPONSE_BODY)

_RESPONSE_HEADERS = {
    'x-response-header1': 'header_value1',
    'x-response-header2': 'header_value2',
    'token': 'some_token_in_response_headers',
    'authorization': 'some_authorization_in_response_headers',
}
_EXPECTED_RESPONSE_HEADERS = {
    **_RESPONSE_HEADERS,
    'token': 'MASKED',
    'authorization': 'MASKED',
}

_EXPECTED_CLIENT_ADDRESS = {'host': 'testclient', 'port': 50000}


@pytest.fixture(scope='session')
def register_middleware() -> Iterable[Mock]:
    """
    .

    """
    logger_mock = Mock()
    logger_mock.info = Mock()

    with patch(target='fastapi_logging_middleware.handlers.get_logger', new=Mock(return_value=logger_mock)):
        LoggingMiddleware().register(app=app)
        yield logger_mock.info


@pytest.fixture()
def logger_mock(register_middleware: Mock) -> Iterable[Mock]:
    try:
        yield register_middleware
    finally:
        register_middleware.reset_mock()


class TestDefaultRegistration:
    """."""

    @pytest.mark.parametrize(
        ('method', 'url_path', 'content', 'params', 'headers', 'response_obj', 'expected_request', 'expected_response'),
        [
            {
                'method': 'POST',
                'url_path': '/',
                'content': _REQUEST_BODY,
                'params': _REQUEST_PARAMS,
                'headers': _REQUEST_HEADERS,
                'response_obj': Response(content=_RESPONSE_BODY, media_type=JSON_MEDIA_TYPE),
                'expected_request': {
                    'query_params': _EXPECTED_REQUEST_PARAMS,
                    'headers': {
                        **_EXPECTED_REQUEST_HEADERS,
                        'content-length': str(_REQUEST_BODY_LEN),
                    },
                },
                'expected_response': {
                    'headers': {
                        'content-type': JSON_MEDIA_TYPE,
                        'content-length': str(_RESPONSE_BODY_LEN),
                    },
                },
            }.values(),
            {
                'method': 'GET',
                'url_path': '/v1/',
                'content': None,
                'params': _REQUEST_PARAMS,
                'headers': _REQUEST_HEADERS,
                'response_obj': Response(content=_RESPONSE_BODY, media_type=JSON_MEDIA_TYPE),
                'expected_request': {
                    'query_params': _EXPECTED_REQUEST_PARAMS,
                    'headers': _EXPECTED_REQUEST_HEADERS,
                },
                'expected_response': {
                    'headers': {
                        'content-type': JSON_MEDIA_TYPE,
                        'content-length': str(_RESPONSE_BODY_LEN),
                    },
                },
            }.values(),
            # GET method without response body
            {
                'method': 'GET',
                'url_path': '/v1/',
                'content': None,
                'params': _REQUEST_PARAMS,
                'headers': _REQUEST_HEADERS,
                'response_obj': Response(status_code=status.HTTP_204_NO_CONTENT),
                'expected_request': {
                    'query_params': _EXPECTED_REQUEST_PARAMS,
                    'headers': _EXPECTED_REQUEST_HEADERS,
                },
                'expected_response': {
                    'headers': {}
                },
            }.values(),
            {
                'method': 'POST',
                'url_path': '/v1/',
                'content': _REQUEST_BODY,
                'params': _REQUEST_PARAMS,
                'headers': _REQUEST_HEADERS,
                'response_obj': Response(content=_RESPONSE_BODY, media_type=JSON_MEDIA_TYPE),
                'expected_request': {
                    'query_params': _EXPECTED_REQUEST_PARAMS,
                    'headers': {
                        **_EXPECTED_REQUEST_HEADERS,
                        'content-length': str(_REQUEST_BODY_LEN),
                    },
                },
                'expected_response': {
                    'headers': {
                        'content-type': JSON_MEDIA_TYPE,
                        'content-length': str(_RESPONSE_BODY_LEN),
                    },
                },
            }.values(),
            # POST method without request/response body
            {
                'method': 'POST',
                'url_path': '/v1/',
                'content': None,
                'params': _REQUEST_PARAMS,
                'headers': _REQUEST_HEADERS,
                'response_obj': Response(status_code=status.HTTP_204_NO_CONTENT),
                'expected_request': {
                    'query_params': _EXPECTED_REQUEST_PARAMS,
                    'headers': {
                        **_EXPECTED_REQUEST_HEADERS,
                        'content-length': '0',
                    },
                },
                'expected_response': {
                    'headers': {},
                },
            }.values(),
        ]
    )
    @pytest.mark.parametrize(argnames='http_client', argvalues=[app], indirect=['http_client'])
    def test_api_route(
            self,
            http_client: TestClient,
            logger_mock: Mock,
            method: str,
            url_path: str,
            content: 'RequestContent',
            params: 'QueryParamTypes',
            headers: 'HeaderTypes',
            response_obj: Response,
            expected_request: Dict,
            expected_response: Dict,
    ):
        """."""
        with patch.object(target=response_getter, attribute='get', new=Mock(return_value=response_obj)):
            http_client.request(method=method, url=url_path, content=content, params=params, headers=headers)

        assert logger_mock.call_count == 2  # 2 - because the request and response are saved
        request = orjson.loads(logger_mock.call_args_list[0].args[0])
        response = orjson.loads(logger_mock.call_args_list[1].args[0])

        expected_full_request = {
            'type': 'Request',
            'method': method,
            'path': url_path,
            'client_address': _EXPECTED_CLIENT_ADDRESS,
        }
        expected_full_request.update(expected_request)
        assert request == expected_full_request
        # check the order of parameters
        assert tuple(request.keys()) == ('type', 'method', 'path', 'query_params', 'headers', 'client_address')

        expected_full_response = {
            'type': 'Response',
            'status_code': response_obj.status_code,
            'request': {
                'method': method,
                'path': url_path,
            },
        }
        expected_full_response.update(expected_response)
        assert response == expected_full_response
        # check the order of parameters
        assert tuple(response.keys()) == ('type', 'status_code', 'headers', 'request')

    @pytest.mark.parametrize(
        ('method', 'url_path', 'content', 'params', 'headers', 'response_obj', 'expected_response'),
        [
            # Swagger GET
            {
                'method': 'GET',
                'url_path': '/docs',
                'content': None,
                'params': _REQUEST_PARAMS,
                'headers': _REQUEST_HEADERS,
                'response_obj': Response(status_code=status.HTTP_200_OK),
                'expected_response': {
                    'headers': {
                        'content-length': '939',
                        'content-type': 'text/html; charset=utf-8'
                    },
                },
            }.values(),
            # Swagger HEAD
            {
                'method': 'HEAD',
                'url_path': '/docs',
                'content': None,
                'params': _REQUEST_PARAMS,
                'headers': _REQUEST_HEADERS,
                'response_obj': Response(status_code=status.HTTP_200_OK),
                'expected_response': {
                    'headers': {
                        'content-length': '939',
                        'content-type': 'text/html; charset=utf-8'
                    },
                },
            }.values(),
            # Redoc GET
            {
                'method': 'GET',
                'url_path': '/redoc',
                'content': None,
                'params': _REQUEST_PARAMS,
                'headers': _REQUEST_HEADERS,
                'response_obj': Response(status_code=status.HTTP_200_OK),
                'expected_response': {
                    'headers': {
                        'content-length': '891',
                        'content-type': 'text/html; charset=utf-8'
                    },
                },
            }.values(),
            # Redoc HEAD
            {
                'method': 'HEAD',
                'url_path': '/redoc',
                'content': None,
                'params': _REQUEST_PARAMS,
                'headers': _REQUEST_HEADERS,
                'response_obj': Response(status_code=status.HTTP_200_OK),
                'expected_response': {
                    'headers': {
                        'content-length': '891',
                        'content-type': 'text/html; charset=utf-8'
                    },
                },
            }.values(),
            # Openapi GET
            {
                'method': 'GET',
                'url_path': '/openapi.json',
                'content': None,
                'params': _REQUEST_PARAMS,
                'headers': _REQUEST_HEADERS,
                'response_obj': Response(status_code=status.HTTP_200_OK),
                'expected_response': {
                    'headers': {
                        'content-length': '932',
                        'content-type': 'application/json'
                    },
                },
            }.values(),
            # Openapi HEAD
            {
                'method': 'HEAD',
                'url_path': '/openapi.json',
                'content': None,
                'params': _REQUEST_PARAMS,
                'headers': _REQUEST_HEADERS,
                'response_obj': Response(status_code=status.HTTP_200_OK),
                'expected_response': {
                    'headers': {
                        'content-length': '932',
                        'content-type': 'application/json'
                    },
                },
            }.values(),
            # oauth2-redirect GET
            {
                'method': 'GET',
                'url_path': '/docs/oauth2-redirect',
                'content': None,
                'params': _REQUEST_PARAMS,
                'headers': _REQUEST_HEADERS,
                'response_obj': Response(status_code=status.HTTP_200_OK),
                'expected_response': {
                    'headers': {
                        'content-length': '3012',
                        'content-type': 'text/html; charset=utf-8'
                    },
                },
            }.values(),
            # oauth2-redirect HEAD
            {
                'method': 'HEAD',
                'url_path': '/docs/oauth2-redirect',
                'content': None,
                'params': _REQUEST_PARAMS,
                'headers': _REQUEST_HEADERS,
                'response_obj': Response(status_code=status.HTTP_200_OK),
                'expected_response': {
                    'headers': {
                        'content-length': '3012',
                        'content-type': 'text/html; charset=utf-8'
                    },
                },
            }.values(),
        ]
    )
    @pytest.mark.parametrize(argnames='http_client', argvalues=[app], indirect=['http_client'])
    def test_base_route(
            self,
            http_client: TestClient,
            logger_mock: Mock,
            method: str,
            url_path: str,
            content: 'RequestContent',
            params: 'QueryParamTypes',
            headers: 'HeaderTypes',
            response_obj: Response,
            expected_response: Dict,
    ):
        """."""
        with patch.object(target=response_getter, attribute='get', new=Mock(return_value=response_obj)):
            http_client.request(method=method, url=url_path, content=content, params=params, headers=headers)

        assert logger_mock.call_count == 1  # 1 - because only the response is saved
        response = orjson.loads(logger_mock.call_args_list[0].args[0])

        expected_full_response = {
            'type': 'Response',
            'status_code': response_obj.status_code,
            'request': {
                'method': method,
                'path': url_path,
            },
        }
        expected_full_response.update(expected_response)
        assert response == expected_full_response
        # check the order of parameters
        assert tuple(response.keys()) == ('type', 'status_code', 'headers', 'request')
