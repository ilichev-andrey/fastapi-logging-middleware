from typing import Callable

from fastapi import Depends
from fastapi.dependencies.utils import get_parameterless_sub_dependant
from fastapi.routing import APIRoute


def add_dependency(route: APIRoute, dependency: Callable) -> None:
    """
    Add a dependency `fastapi.Depends` for the API endpoint.

    Args:
        route: Endpoint route object.
        dependency: Dependency to add.
    """
    route.dependencies.append(Depends(dependency))

    # The loop code block is taken from the initialization of the class object `fastapi.APIRoute`
    # https://github.com/tiangolo/fastapi/blob/0.88.0/fastapi/routing.py#L439-L443
    for depends in route.dependencies[::-1]:
        route.dependant.dependencies.insert(
            0,
            get_parameterless_sub_dependant(depends=depends, path=route.path_format),
        )
