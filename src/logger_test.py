import contextlib
import textwrap

from loguru import logger
import pytest
from pytest import LogCaptureFixture

from .logger import describe, log_level_name


@pytest.fixture
def log_level() -> str:
    return "TRACE"


@pytest.fixture(autouse=True)
def log_cleanly(log_cleanly: None) -> None: ...


@pytest.mark.typed
def test_logger_context_manager_success_trace(caplog: LogCaptureFixture) -> None:
    def log() -> None:
        logger.info("working")

    with describe("context test"):
        log()
    assert (
        caplog.text.strip()
        == textwrap.dedent(
            """
            context test ...
            working
            context test [done]
            """
        ).strip()
    )


@pytest.mark.typed
def test_logger_context_manager_failure_trace(caplog: LogCaptureFixture) -> None:
    def log() -> None:
        logger.info("working")
        raise RuntimeError("not working")

    with pytest.raises(RuntimeError), describe("context test"):
        log()
    assert (
        caplog.text.strip()
        == textwrap.dedent(
            """
            context test ...
            working
            context test [failed]
            """
        ).strip()
    )


# Override log level for this test.
@pytest.mark.parametrize("log_level", ["INFO"])
def test_logger_context_manager_level(caplog: LogCaptureFixture) -> None:
    def log() -> None:
        logger.info("working")

    with describe("info test", level="INFO"):
        log()
    with describe("debug test", level="DEBUG"):
        log()
    with describe("error test", level="ERROR"):
        log()

    assert (
        caplog.text.strip()
        == textwrap.dedent(
            """
            info test ...
            working
            info test [done]
            working
            error test ...
            working
            error test [done]
            """
        ).strip()
    )


# Override log level for this test.
@pytest.mark.parametrize("log_level", ["INFO"])
def test_logger_context_manager_error_level(caplog: LogCaptureFixture) -> None:
    def log() -> None:
        logger.info("failing")
        raise RuntimeError()

    with (
        contextlib.suppress(RuntimeError),
        describe("error test", level="INFO", error_level="ERROR"),
    ):
        log()
    with (
        contextlib.suppress(RuntimeError),
        describe("debug test", level="ERROR", error_level="DEBUG"),
    ):
        log()
    with (
        contextlib.suppress(RuntimeError),
        describe("trace test", level="DEBUG", error_level="INFO"),
    ):
        log()

    assert (
        caplog.text.strip()
        == textwrap.dedent(
            """
            error test ...
            failing
            error test [failed]
            debug test ...
            failing
            failing
            trace test [failed]
            """
        ).strip()
    )


@pytest.mark.typed
def test_logger_wrap_success_trace(caplog: LogCaptureFixture) -> None:
    def log(x: int) -> int:
        logger.info("doing")
        return x + 1

    assert describe("wrap test")(log)(3) == 4

    assert (
        caplog.text.strip()
        == textwrap.dedent(
            """
            wrap test ...
            doing
            wrap test [done]
            """
        ).strip()
    )


@pytest.mark.typed
def test_logger_wrap_failure_trace(caplog: LogCaptureFixture) -> None:
    def log(x: int) -> int:
        logger.info("doing")
        raise RuntimeError()

    with pytest.raises(RuntimeError):
        describe("wrap test")(log)(3)

    assert (
        caplog.text.strip()
        == textwrap.dedent(
            """
            wrap test ...
            doing
            wrap test [failed]
            """
        ).strip()
    )


@pytest.mark.parametrize(
    "quiet, verbose, level",
    [
        # default
        (0, 0, "info"),
        # -v
        (0, 1, "debug"),
        # -vv
        (0, 2, "trace"),
        # -vvv
        (0, 3, 50),
        # -vvvv
        (0, 4, 50),
        # -q
        (1, 0, "error"),
        # -qq
        (2, 0, "critical"),
        # -qqq
        (3, 0, 0),
        # -qqqq
        (4, 0, 0),
        # mixed equally
        (1, 1, "info"),
        # mixed verbose
        (1, 2, "debug"),
        # mixed quiet
        (2, 1, "error"),
    ],
)
def test_log_level_name(quiet: int, verbose: int, level: str | int) -> None:
    if isinstance(level, str):
        assert log_level_name(quiet, verbose) == level.upper()
    else:
        assert log_level_name(quiet, verbose) == level
