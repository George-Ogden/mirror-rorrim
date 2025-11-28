import os
import shutil
import tempfile

import git
import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.extensions.amber import AmberSnapshotExtension
from syrupy.location import PyTestLocation
from syrupy.types import SnapshotIndex

from .diff import Diff
from .typed_path import AbsDir, AbsFile, RelDir, RelFile


@pytest.fixture
def test_data_path(global_test_data_path: AbsDir) -> AbsDir:
    return global_test_data_path / RelDir("diff_tests")


class DifferentNameExtension(AmberSnapshotExtension):
    location: AbsFile

    @classmethod
    def get_location(cls, *, test_location: PyTestLocation, index: SnapshotIndex = 0) -> str:
        return os.fspath(cls.location)


@pytest.fixture
def snapshot(
    snapshot: SnapshotAssertion, test_data_path: AbsDir, filepath: RelFile
) -> SnapshotAssertion:
    DifferentNameExtension.location = test_data_path / RelDir("snapshots") / filepath
    return snapshot.use_extension(DifferentNameExtension)


@pytest.mark.parametrize("filepath", map(RelFile, ["empty", "new", "conflict"]))
def test_diff_apply(
    filepath: RelFile, test_data_path: AbsDir, snapshot: SnapshotAssertion, typed_tmp_path: AbsDir
) -> None:
    remote = AbsDir(tempfile.mkdtemp())
    shutil.copytree(test_data_path / RelDir("remote"), remote, dirs_exist_ok=True)
    # gitpython-developers/GitPython#2085
    git.Repo.init(os.fspath(remote))
    diff = Diff.new_file(remote, filepath)
    tmp_filepath = typed_tmp_path / filepath
    tmp_filepath.path.parent.mkdir(parents=True, exist_ok=True)
    current_path = test_data_path / RelDir("current") / filepath
    if current_path.exists():
        shutil.copy2(current_path, tmp_filepath)
    # gitpython-developers/GitPython#2085
    git.Repo.init(os.fspath(typed_tmp_path))
    diff.apply(typed_tmp_path)
    with open(tmp_filepath) as f:
        assert f.read() == snapshot
