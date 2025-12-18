import abc
from collections.abc import Callable
from dataclasses import KW_ONLY, dataclass
import functools
import inspect
import sys
from types import TracebackType
from typing import ClassVar, Literal

from loguru import logger

from .constants import DONE_SUFFIX, FAILURE_SUFFIX, LOADING_SUFFIX
from .utils import strict_cast


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
        logger.opt(depth=self.depth).log(self.level, message)

    def error_log(self, message: str, /) -> None:
        logger.opt(depth=self.depth).log(self.error_level, message)

    @property
    def depth(self) -> int:
        """Return the depth of the first frame not in the file."""
        for depth, frameinfo in enumerate(inspect.stack(), start=-1):
            if frameinfo.filename != __file__:
                return depth
        # Fallback if cannot determine caller.
        return 0

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


class ProgramState(abc.ABC):
    type CommandName = Literal["install", "sync", "check"]
    command: ClassVar[CommandName]

    @abc.abstractmethod
    def __init__(self) -> None: ...
    @classmethod
    def record_command[**P, R](cls, command: Callable[P, R]) -> Callable[P, R]:
        command_name = strict_cast(cls.CommandName, command.__name__)

        @functools.wraps(command)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            cls.command = command_name
            return command(*args, **kwargs)

        return wrapper


def log_level_name(quiet: int, verbose: int) -> str | int:
    match verbose - quiet:
        case -3:
            return "CRITICAL"
        case -2:
            return "ERROR"
        case -1:
            return "WARNING"
        case 0:
            return "INFO"
        case 1:
            return "DEBUG"
        case 2:
            return "TRACE"
        case n if n < 0:
            return 0
        case n if n > 0:
            return 50
    raise TypeError()


def setup_logger(quiet: int, verbose: int) -> None:
    logger.remove()
    logger.add(sys.stdout, level=log_level_name(quiet, verbose), format="<level>{message}</level>")
