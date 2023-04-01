import logging
from functools import wraps
from typing import Any, Concatenate, ParamSpec, TypeVar, Callable

P = ParamSpec("P")
T = TypeVar("T")
F = TypeVar("F")


def copy_method_signature(
    source: Callable[Concatenate[Any, P], T]
) -> Callable[[Callable[..., T]], Callable[Concatenate[Any, P], T]]:

    def wrapper(target: Callable[..., T]) -> Callable[Concatenate[Any, P], T]:

        @wraps(source)
        def wrapped(self: Any, /, *args: P.args, **kwargs: P.kwargs) -> T:
            return target(self, *args, **kwargs)

        return wrapped

    return wrapper


class LoggerMixin(object):

    def __init__(self, name=__file__):
        self._logger = logging.getLogger(name)

    @copy_method_signature(logging.info)
    def info(self, *args, **kwargs):
        self._logger.info(*args, **kwargs)

    @copy_method_signature(logging.error)
    def error(self, *args, **kwargs):
        self._logger.error(*args, **kwargs)

    @copy_method_signature(logging.warning)
    def warning(self, *args, **kwargs):
        self._logger.warning(*args, **kwargs)

    @copy_method_signature(logging.debug)
    def debug(self, *args, **kwargs):
        self._logger.debug(*args, **kwargs)
