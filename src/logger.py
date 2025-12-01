from collections.abc import Callable
from dataclasses import dataclass
import functools
from types import TracebackType

from loguru import logger

from .constants import DONE_SUFFIX, FAILURE_SUFFIX, LOADING_SUFFIX


@dataclass(frozen=True, slots=True)
class describe:  # noqa: N801
    message: str

    def __call__[**P, R](self, fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def logging_fn(*args: P.args, **kwargs: P.kwargs) -> R:
            with self:
                return fn(*args, **kwargs)

        return logging_fn

    @property
    def start_message(self) -> str:
        return f"{self.message} {LOADING_SUFFIX}"

    @property
    def done_message(self) -> str:
        return f"{self.message} {DONE_SUFFIX}"

    @property
    def failed_message(self) -> str:
        return f"{self.message} {FAILURE_SUFFIX}"

    def __enter__(self) -> None:
        logger.trace(self.start_message)

    def __exit__(
        self,
        type_: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if type_ is None:
            logger.trace(self.done_message)
        else:
            logger.error(self.failed_message)
