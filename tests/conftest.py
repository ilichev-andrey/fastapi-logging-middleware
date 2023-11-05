from typing import Iterator

import pytest
from _pytest.fixtures import SubRequest
from starlette.testclient import TestClient


@pytest.fixture()
def http_client(request: SubRequest) -> Iterator[TestClient]:
    """A fixture that initializes the HTTP client."""
    with TestClient(app=request.param, base_url='http://test') as client_obj:
        yield client_obj
