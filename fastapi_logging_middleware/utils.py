from logging import getLogger, Logger
from typing import Any, Optional, Callable

from orjson import orjson

UTF8 = 'utf-8'


def get_logger() -> Logger:
    """Get a default logging object."""
    return getLogger('fastapi_logging_middleware')


SerializerType = Callable[[Any], Any]


def orjson_dumps(obj: Any, *, default: Optional[SerializerType] = None, option: int = orjson.OPT_NON_STR_KEYS) -> str:
    """Convert `obj` to JSON format."""
    return orjson.dumps(obj, default=default, option=option).decode(encoding=UTF8)
