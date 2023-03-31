import logging
from typing import Generic, Callable, Any, TypeVar

F = TypeVar("F")

class copy_signature(Generic[F]):
    def __init__(self, target: F) -> None:
        ...

    def __call__(self, wrapped: Callable[..., Any]) -> F:
        ...


def f(x: bool, *extra: int) -> str:
    ...


class LoggerMixin(object):
    def __init__(self):
        self._logger = logging.getLogger(__file__)

    @copy_signature(logging.info)
    def info(self, *args, **kwargs):
        self._logger.info(*args, **kwargs)

    @copy_signature(logging.error)
    def error(self, *args, **kwargs):
        self._logger.error(*args, **kwargs)

    @copy_signature(logging.warning)
    def warning(self, *args, **kwargs):
        self._logger.warning(*args, **kwargs)

    @copy_signature(logging.debug)
    def debug(self, *args, **kwargs):
        self._logger.debug(*args, **kwargs)
