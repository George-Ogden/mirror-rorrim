import os
from pathlib import Path

import git
import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.extensions.amber import AmberSnapshotExtension
from syrupy.location import PyTestLocation
from syrupy.types import SnapshotIndex

from .constants import MIRROR_LOCK
from .typed_path import AbsDir, AbsFile, RelDir, RelFile


@pytest.fixture
def global_test_data_path() -> AbsDir:
    return AbsDir(Path(__file__).absolute().parent.parent / "test_data")


@pytest.fixture
def typed_tmp_path(tmp_path: Path) -> AbsDir:
    return AbsDir(tmp_path)


@pytest.fixture
def local_git_repo(typed_tmp_path: AbsDir) -> AbsDir:
    # gitpython-developers/GitPython#2085
    git.Repo.init(os.fspath(typed_tmp_path))
    return typed_tmp_path


@pytest.fixture
def tmp_lock_path(typed_tmp_path: AbsDir) -> AbsFile:
    return typed_tmp_path / MIRROR_LOCK


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
