from collections.abc import Generator
import os
from pathlib import Path
import sys
import textwrap

import git
from loguru import logger
import pytest
from pytest import FixtureRequest, LogCaptureFixture
from syrupy.assertion import SnapshotAssertion
from syrupy.extensions.amber import AmberSnapshotExtension
from syrupy.location import PyTestLocation
from syrupy.types import SnapshotIndex
import yaml
from yaml import Node

from .logger import ProgramState
from .typed_path import AbsDir, AbsFile, GitDir, RelDir, RelFile


@pytest.fixture
def global_test_data_path() -> AbsDir:
    return AbsDir(Path(__file__).absolute().parent.parent / "test_data")


@pytest.fixture
def typed_tmp_path(tmp_path: Path) -> AbsDir:
    return AbsDir(tmp_path)


@pytest.fixture
def local_git_repo(typed_tmp_path: AbsDir, request: FixtureRequest) -> Generator[GitDir]:
    git.Repo.init(typed_tmp_path)
    os.chdir(typed_tmp_path)
    yield GitDir(typed_tmp_path)
    os.chdir(request.config.invocation_params.dir)


class DifferentNameExtension(AmberSnapshotExtension):
    location: AbsFile

    @classmethod
    def get_location(cls, *, test_location: PyTestLocation, index: SnapshotIndex = 0) -> str:
        return os.fspath(cls.location)


@pytest.fixture
def snapshot(
    snapshot: SnapshotAssertion, test_data_path: AbsDir, test_name: str
) -> SnapshotAssertion:
    DifferentNameExtension.location = test_data_path / RelDir("snapshots") / RelFile(test_name)
    return snapshot.use_extension(DifferentNameExtension)


@pytest.fixture(autouse=True)
def log_everything() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level="TRACE",
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{file.path}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )


@pytest.fixture
def log_cleanly(caplog: LogCaptureFixture, log_level: str) -> None:
    logger.remove()
    logger.add(caplog.handler, level=log_level, colorize=False, format="{message}")


@pytest.fixture
def yaml_node(raw_yaml: str) -> Node:
    raw_yaml = textwrap.dedent(raw_yaml).strip()
    return yaml.compose(raw_yaml, Loader=yaml.SafeLoader)


@pytest.fixture(autouse=True)
def set_mock_command() -> None:
    ProgramState.command = "test"  # type: ignore [assignment]
