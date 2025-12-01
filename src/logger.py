from collections.abc import Callable
from dataclasses import KW_ONLY, dataclass
import functools
from types import TracebackType

from loguru import logger

from .constants import DONE_SUFFIX, FAILURE_SUFFIX, LOADING_SUFFIX


@dataclass(frozen=True, slots=True)
class describe:  # noqa: N801
    message: str
    _: KW_ONLY
    level: str = "TRACE"
    error_level: str = "ERROR"

    @property
    def start_message(self) -> str:
        return f"{self.message} {LOADING_SUFFIX}"

    @property
    def done_message(self) -> str:
        return f"{self.message} {DONE_SUFFIX}"

    @property
    def failed_message(self) -> str:
        return f"{self.message} {FAILURE_SUFFIX}"

    def log(self, message: str, /) -> None:
        logger.log(self.level, message)

    def error_log(self, message: str, /) -> None:
        logger.log(self.error_level, message)

    def __enter__(self) -> None:
        self.log(self.start_message)

    def __exit__(
        self,
        type_: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if type_ is None:
            self.log(self.done_message)
        else:
            self.error_log(self.failed_message)

    def __call__[**P, R](self, fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def logging_fn(*args: P.args, **kwargs: P.kwargs) -> R:
            with self:
                return fn(*args, **kwargs)

        return logging_fn
