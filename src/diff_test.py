import os
import shutil
import tempfile

import git
import pytest
from syrupy.assertion import SnapshotAssertion

from .diff import Diff
from .file import MirrorFile
from .test_utils import quick_mirror_file
from .typed_path import AbsDir, RelDir


@pytest.fixture
def test_data_path(global_test_data_path: AbsDir) -> AbsDir:
    return global_test_data_path / RelDir("diff_tests")


@pytest.fixture
def test_name(file: MirrorFile) -> str:
    return os.fspath(file.target)


@pytest.mark.parametrize(
    "file",
    [
        quick_mirror_file("empty"),
        quick_mirror_file("new"),
        quick_mirror_file("conflict"),
        quick_mirror_file("new", "rename"),
    ],
)
def test_diff_apply(
    file: MirrorFile, test_data_path: AbsDir, snapshot: SnapshotAssertion, typed_tmp_path: AbsDir
) -> None:
    remote = AbsDir(tempfile.mkdtemp())
    shutil.copytree(test_data_path / RelDir("remote"), remote, dirs_exist_ok=True)
    # gitpython-developers/GitPython#2085
    git.Repo.init(os.fspath(remote))
    diff = Diff.new_file(remote, file)
    tmp_filepath = typed_tmp_path / file.target
    tmp_filepath.path.parent.mkdir(parents=True, exist_ok=True)
    current_path = test_data_path / RelDir("local") / file.target
    if current_path.exists():
        shutil.copy2(current_path, tmp_filepath)
    # gitpython-developers/GitPython#2085
    git.Repo.init(os.fspath(typed_tmp_path))
    diff.apply(typed_tmp_path)
    with open(tmp_filepath) as f:
        assert f.read() == snapshot
