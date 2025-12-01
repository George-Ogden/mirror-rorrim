import textwrap

from loguru import logger
import pytest
from pytest import LogCaptureFixture  # noqa: PT013

from .logger import describe


@pytest.fixture(autouse=True)
def log_cleanly(caplog: LogCaptureFixture) -> None:
    logger.remove()
    logger.add(caplog.handler, level="TRACE", colorize=False, format="{message}")
    caplog.set_level(0)


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
