from typing import Dict

import pytest
from starlette import status
from starlette.datastructures import Headers, QueryParams, MutableHeaders

from fastapi_logging_middleware import http_exporter


class TestRequestPrivateParameterMasking:
    """Test the masking of private data contained in the request."""

    @pytest.mark.parametrize(
        ('obj', 'masked_names', 'expected_not_masked', 'expected_masked'),
        [
            {
                'obj': http_exporter.RequestInfo(
                    method='POST',
                    path='/api/v1/test-masking',
                    query_params=QueryParams([
                        ('param_name1', 'param_value1'),
                        ('param_name2', 'param_value2'),
                        ('authorization', 'some_authorization'),
                        ('token', 'some_token'),
                        ('custom_auth_param', 'some_custom_auth_param'),
                    ]),
                    headers=Headers({
                        'header-name1': 'header_value1',
                        'header-name2': 'header_value2',
                        'authorization': 'some authorization',
                        'token': 'some token',
                        'custom-auth-header': 'some custom auth',
                    }),
                ),
                'masked_names': {*http_exporter.DEFAULT_MASKED_NAMES, 'custom_auth_param', 'custom-auth-header'},
                'expected_not_masked': {
                    'type': 'Request',
                    'method': 'POST',
                    'path': '/api/v1/test-masking',
                    'query_params': (
                        'param_name1=param_value1&'
                        'param_name2=param_value2&'
                        'authorization=some_authorization&'
                        'token=some_token&'
                        'custom_auth_param=some_custom_auth_param'
                    ),
                    'headers': {
                        'header-name1': 'header_value1',
                        'header-name2': 'header_value2',
                        'authorization': 'some authorization',
                        'token': 'some token',
                        'custom-auth-header': 'some custom auth',
                    }
                },
                'expected_masked': {
                    'type': 'Request',
                    'method': 'POST',
                    'path': '/api/v1/test-masking',
                    'query_params': (
                        'param_name1=param_value1&'
                        'param_name2=param_value2&'
                        'authorization=MASKED&'
                        'token=MASKED&'
                        'custom_auth_param=MASKED'
                    ),
                    'headers': {
                        'header-name1': 'header_value1',
                        'header-name2': 'header_value2',
                        'authorization': 'MASKED',
                        'token': 'MASKED',
                        'custom-auth-header': 'MASKED',
                    }
                },
            }.values()
        ]
    )
    def test_as_dict(
            self,
            obj: http_exporter.RequestInfo,
            masked_names: http_exporter.MaskedNamesType,
            expected_not_masked: Dict,
            expected_masked: Dict,
    ):
        """
        Test the masking of private data when converting to a dictionary.
        By default, the data is masked.
        """
        actual = obj.as_dict(masked_names=masked_names)
        assert actual == expected_masked

        actual = obj.as_dict(is_mask_private_data=False)
        assert actual == expected_not_masked

    @pytest.mark.parametrize(
        ('obj', 'masked_names', 'expected'),
        [
            {
                'obj': http_exporter.RequestInfo(
                    method='POST',
                    path='/api/v1/test-masking',
                    query_params=QueryParams([
                        ('param_name1', 'param_value1'),
                        ('param_name2', 'param_value2'),
                        ('authorization', 'some_authorization'),
                        ('token', 'some_token'),
                        ('custom_auth_param', 'some_custom_auth_param'),
                    ]),
                    headers=Headers({
                        'header-name1': 'header_value1',
                        'header-name2': 'header_value2',
                        'authorization': 'some authorization',
                        'token': 'some token',
                        'custom-auth-header': 'some custom auth',
                    }),
                ),
                'masked_names': {*http_exporter.DEFAULT_MASKED_NAMES, 'custom_auth_param', 'custom-auth-header'},
                'expected': http_exporter.RequestInfo(
                    method='POST',
                    path='/api/v1/test-masking',
                    query_params=QueryParams([
                        ('param_name1', 'param_value1'),
                        ('param_name2', 'param_value2'),
                        ('authorization', 'MASKED'),
                        ('token', 'MASKED'),
                        ('custom_auth_param', 'MASKED'),
                    ]),
                    headers=Headers({
                        'header-name1': 'header_value1',
                        'header-name2': 'header_value2',
                        'authorization': 'MASKED',
                        'token': 'MASKED',
                        'custom-auth-header': 'MASKED',
                    }),
                ),
            }.values()
        ]
    )
    def test_copy_object_without_private_data(
            self,
            obj: http_exporter.RequestInfo,
            masked_names: http_exporter.MaskedNamesType,
            expected: http_exporter.RequestInfo
    ):
        """
        Test of the mask_private_data function.
        A copy of the object will be created, but with masked data.
        """
        actual = obj.mask_private_data(masked_names=masked_names)
        assert actual == expected


class TestResponsePrivateParameterMasking:
    """Test the masking of private data contained in the response."""

    @pytest.mark.parametrize(
        ('obj', 'masked_names', 'expected_not_masked', 'expected_masked'),
        [
            {
                'obj': http_exporter.ResponseInfo(
                    status_code=status.HTTP_200_OK,
                    headers=MutableHeaders({
                        'header-name1': 'header_value1',
                        'header-name2': 'header_value2',
                        'authorization': 'some authorization',
                        'token': 'some token',
                        'custom-auth-header': 'some custom auth',
                    }),
                ),
                'masked_names': {*http_exporter.DEFAULT_MASKED_NAMES, 'custom-auth-header'},
                'expected_not_masked': {
                    'type': 'Response',
                    'status_code': status.HTTP_200_OK,
                    'headers': {
                        'header-name1': 'header_value1',
                        'header-name2': 'header_value2',
                        'authorization': 'some authorization',
                        'token': 'some token',
                        'custom-auth-header': 'some custom auth',
                    }
                },
                'expected_masked': {
                    'type': 'Response',
                    'status_code': status.HTTP_200_OK,
                    'headers': {
                        'header-name1': 'header_value1',
                        'header-name2': 'header_value2',
                        'authorization': 'MASKED',
                        'token': 'MASKED',
                        'custom-auth-header': 'MASKED',
                    }
                }
            }.values()
        ]
    )
    def test_as_dict(
            self,
            obj: http_exporter.ResponseInfo,
            masked_names: http_exporter.MaskedNamesType,
            expected_not_masked: Dict,
            expected_masked: Dict,
    ):
        """
        Test the masking of private data when converting to a dictionary.
        By default, the data is masked.
        """
        actual = obj.as_dict(masked_names=masked_names)
        assert actual == expected_masked

        actual = obj.as_dict(is_mask_private_data=False)
        assert actual == expected_not_masked

    @pytest.mark.parametrize(
        ('obj', 'masked_names', 'expected'),
        [
            {
                'obj': http_exporter.ResponseInfo(
                    status_code=status.HTTP_200_OK,
                    headers=MutableHeaders({
                        'header-name1': 'header_value1',
                        'header-name2': 'header_value2',
                        'authorization': 'some authorization',
                        'token': 'some token',
                        'custom-auth-header': 'some custom auth',
                    }),
                ),
                'masked_names': {*http_exporter.DEFAULT_MASKED_NAMES, 'custom-auth-header'},
                'expected': http_exporter.ResponseInfo(
                    status_code=status.HTTP_200_OK,
                    headers=MutableHeaders({
                        'header-name1': 'header_value1',
                        'header-name2': 'header_value2',
                        'authorization': 'MASKED',
                        'token': 'MASKED',
                        'custom-auth-header': 'MASKED',
                    }),
                ),
            }.values()
        ]
    )
    def test_copy_object_without_private_data(
            self,
            obj: http_exporter.ResponseInfo,
            masked_names: http_exporter.MaskedNamesType,
            expected: http_exporter.ResponseInfo
    ):
        """
        Test of the mask_private_data function.
        A copy of the object will be created, but with masked data.
        """
        actual = obj.mask_private_data(masked_names=masked_names)
        assert actual == expected
