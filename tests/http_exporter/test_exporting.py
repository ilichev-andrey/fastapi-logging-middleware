from pathlib import Path
from typing import Dict, TYPE_CHECKING, List, Iterable, Union, Mapping
from unittest.mock import patch, Mock

import pytest
from fastapi import FastAPI, APIRouter, Depends, UploadFile, File
from starlette.datastructures import Headers
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, FileResponse
from starlette.testclient import TestClient

from fastapi_logging_middleware import http_exporter
from tests.components import Logger, ResponseGetter, JSON_MEDIA_TYPE

if TYPE_CHECKING:
    from httpx._types import RequestContent, QueryParamTypes, HeaderTypes, RequestFiles

_DATA_DIR = Path(__file__).parent.joinpath('data').resolve()

# ---- Test components ----
_logger = Logger()
_response_getter = ResponseGetter()


# ---- Application components ----
async def _save_request(request: Request) -> None:
    request_info = await http_exporter.RequestInfo.from_starlette_request(
        request=request,
        include_body=True,
        include_form=True
    )
    _logger.log('', extra=request_info.as_dict())


async def _save_response(request: Request, call_next: RequestResponseEndpoint) -> Response:
    response = await call_next(request)
    response_info = await http_exporter.ResponseInfo.from_starlette_response(
        response=response,
        include_body=True,
        request=request
    )
    _logger.log('', extra=response_info.as_dict())
    return response


_router = APIRouter()


@_router.post('/test-exporting', response_class=Response, dependencies=[Depends(_save_request)])
async def _post():
    return _response_getter.get()


@_router.post('/test-exporting/files', response_class=Response, dependencies=[Depends(_save_request)])
async def _post_files(files: List[UploadFile] = File()):
    for file in files:
        await file.read()
    return _response_getter.get()


_app = FastAPI()
_app.include_router(_router, prefix='/api/v1')
_app.add_middleware(BaseHTTPMiddleware, dispatch=_save_response)


# ---- Tests ----
_REQUEST_BODY = b'{"request_body": "ok"}'
_REQUEST_BODY_LEN = len(_REQUEST_BODY)
_RESPONSE_BODY = b'{"response_body": "ok"}'
_RESPONSE_BODY_LEN = len(_RESPONSE_BODY)

_EXPECTED_CLIENT_ADDRESS = {'host': 'testclient', 'port': 50000}


class TestRequestResponseExporting:
    """Various cases of exporting request/response objects are checked to record this data in the log."""

    @pytest.mark.parametrize(
        ('content', 'params', 'headers', 'response_obj', 'expected_request', 'expected_response'),
        [
            {
                'content': _REQUEST_BODY,
                'params': [('param_list', 'list_item1'), ('param_list', 'list_item2')],
                'headers': {'request-header1': 'request_header_value1', 'request-header2': 'request_header_value2'},
                'response_obj': Response(content=_RESPONSE_BODY, media_type=JSON_MEDIA_TYPE),
                'expected_request': {
                    'query_params': 'param_list=list_item1&param_list=list_item2',
                    'headers': {
                        'accept': '*/*',
                        'accept-encoding': 'gzip, deflate',
                        'connection': 'keep-alive',
                        'content-length': str(_REQUEST_BODY_LEN),
                        'host': 'test',
                        'user-agent': 'testclient',
                        'request-header1': 'request_header_value1',
                        'request-header2': 'request_header_value2'
                    },
                },
                'expected_response': {
                    'headers': {
                        'content-type': JSON_MEDIA_TYPE,
                        'content-length': str(_RESPONSE_BODY_LEN),
                    },
                },
            }.values(),
            # The text in the body is not in English
            {
                'content': 'какой-то текст в запросе'.encode(),
                'params': {},
                'headers': {},
                'response_obj': Response(content='какой-то текст в ответе'.encode(), media_type='text/plain'),
                'expected_request': {
                    'query_params': '',
                    'headers': {
                        'accept': '*/*',
                        'accept-encoding': 'gzip, deflate',
                        'connection': 'keep-alive',
                        'content-length': str(len('какой-то текст в запросе'.encode())),
                        'host': 'test',
                        'user-agent': 'testclient',
                    },
                },
                'expected_response': {
                    'headers': {
                        'content-type': 'text/plain; charset=utf-8',
                        'content-length': str(len('какой-то текст в ответе'.encode())),
                    },
                },
            }.values()
        ]
    )
    @pytest.mark.parametrize(argnames='http_client', argvalues=[_app], indirect=['http_client'])
    def test_text_request_text_response(
            self,
            http_client: TestClient,
            content: 'RequestContent',
            params: 'QueryParamTypes',
            headers: 'HeaderTypes',
            response_obj: Response,
            expected_request: Dict,
            expected_response: Dict,
    ):
        """The export of request/response data arriving in the usual format is checked."""
        logger_mock = Mock()
        url_path = '/api/v1/test-exporting'

        with patch.object(target=_response_getter, attribute='get', new=Mock(return_value=response_obj)):
            with patch.object(target=_logger, attribute='log', new=logger_mock):
                http_client.post(url=url_path, content=content, params=params, headers=headers)

        assert logger_mock.call_count == 2  # 2 - because the request and response are saved
        request = logger_mock.call_args_list[0].kwargs['extra']
        response = logger_mock.call_args_list[1].kwargs['extra']

        expected_full_request = {
            'type': 'Request',
            'method': 'POST',
            'path': url_path,
            'client_address': _EXPECTED_CLIENT_ADDRESS,
            'body': str(content),
        }
        expected_full_request.update(expected_request)
        assert request == expected_full_request
        # check the order of parameters
        assert tuple(request.keys()) == ('type', 'method', 'path', 'query_params', 'headers', 'client_address', 'body')

        expected_full_response = {
            'type': 'Response',
            'status_code': response_obj.status_code,
            'request': {
                'method': 'POST',
                'path': url_path,
            },
            'body': str(response_obj.body),
        }
        expected_full_response.update(expected_response)
        assert response == expected_full_response
        # check the order of parameters
        assert tuple(response.keys()) == ('type', 'status_code', 'headers', 'request', 'body')

    @pytest.mark.parametrize(
        ('data', 'files', 'params', 'headers', 'response_obj', 'expected_request', 'expected_response'),
        [
            {
                'data': {
                    'param_data_name1': 'param_data_value1',
                    'param_data_name2': 'param_data_value2',
                },
                'files': [
                    ('files', ('text_file_1.txt', _DATA_DIR.joinpath('text_file_1.txt').read_bytes())),
                    ('files', ('text_file_2.txt', _DATA_DIR.joinpath('text_file_2.txt').read_bytes())),
                ],
                'params': [('param_list', 'list_item1'), ('param_list', 'list_item2')],
                'headers': {'request-header1': 'request_header_value1', 'request-header2': 'request_header_value2'},
                'response_obj': FileResponse(path=_DATA_DIR.joinpath('text_file_3.txt')),
                'expected_request': {
                    'query_params': 'param_list=list_item1&param_list=list_item2',
                    'headers': {
                        'accept': '*/*',
                        'accept-encoding': 'gzip, deflate',
                        'connection': 'keep-alive',
                        'content-length': '2839',
                        'content-type': 'multipart/form-data; boundary=',
                        'host': 'test',
                        'user-agent': 'testclient',
                        'request-header1': 'request_header_value1',
                        'request-header2': 'request_header_value2'
                    },
                    'form': [
                        ('param_data_name1', 'param_data_value1'),
                        ('param_data_name2', 'param_data_value2'),
                        (
                            'files',
                            {
                                'file_name': 'text_file_1.txt',
                                'headers': Headers({
                                    'content-disposition': 'form-data; name="files"; filename="text_file_1.txt"',
                                    'content-type': 'text/plain'
                                }),
                                'size': 807
                            }
                        ),
                        (
                            'files',
                            {
                                'file_name': 'text_file_2.txt',
                                'headers': Headers({
                                    'content-disposition': 'form-data; name="files"; filename="text_file_2.txt"',
                                    'content-type': 'text/plain'
                                }),
                                'size': 1486
                            }
                        ),
                    ],
                },
                'expected_response': {
                    'headers': {
                        'content-length': '1996',
                        'content-type': 'text/plain; charset=utf-8',
                        'etag': 'a64451cf7a4688b5a56bc104955da99b',
                        'last-modified': 'Mon, 13 Nov 2023 12:17:57 GMT'
                    },
                    'body': str(_DATA_DIR.joinpath('text_file_3.txt').read_bytes())
                },
            }.values(),
        ]
    )
    @pytest.mark.parametrize(argnames='http_client', argvalues=[_app], indirect=['http_client'])
    def test_form_data_request_file_response(
            self,
            http_client: TestClient,
            data: Mapping[str, Union[str, Iterable[str]]],
            files: 'RequestFiles',
            params: 'QueryParamTypes',
            headers: 'HeaderTypes',
            response_obj: Response,
            expected_request: Dict,
            expected_response: Dict,
    ):
        """."""

        logger_mock = Mock()
        url_path = '/api/v1/test-exporting/files'

        with patch.object(target=_response_getter, attribute='get', new=Mock(return_value=response_obj)):
            with patch.object(target=_logger, attribute='log', new=logger_mock):
                http_client.post(url=url_path, params=params, headers=headers, data=data, files=files)

        assert logger_mock.call_count == 2  # 2 - because the request and response are saved
        request: Dict = logger_mock.call_args_list[0].kwargs['extra']
        response: Dict = logger_mock.call_args_list[1].kwargs['extra']

        # check the content-type from the headers
        content_type = request['headers'].pop('content-type')
        expected_content_type = expected_request['headers'].pop('content-type')
        assert content_type.startswith(expected_content_type)

        expected_full_request = {
            'type': 'Request',
            'method': 'POST',
            'path': url_path,
            'client_address': _EXPECTED_CLIENT_ADDRESS,
        }
        expected_full_request.update(expected_request)
        assert request == expected_full_request
        # check the order of parameters
        assert tuple(request.keys()) == ('type', 'method', 'path', 'query_params', 'headers', 'client_address', 'form')

        expected_full_response = {
            'type': 'Response',
            'status_code': response_obj.status_code,
            'request': {
                'method': 'POST',
                'path': url_path,
            },
        }
        expected_full_response.update(expected_response)
        assert response == expected_full_response
        # check the order of parameters
        assert tuple(response.keys()) == ('type', 'status_code', 'headers', 'request', 'body')
