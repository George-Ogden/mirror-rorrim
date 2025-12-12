import os
import shutil
import tempfile

import pytest
from syrupy.assertion import SnapshotAssertion

from .diff import Diff
from .file import MirrorFile
from .test_utils import add_commit, quick_mirror_file
from .typed_path import AbsDir, GitDir, RelDir


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
        quick_mirror_file("empty", "new-empty"),
        quick_mirror_file("new", "nested/folder/new"),
    ],
)
def test_diff_apply(
    file: MirrorFile, test_data_path: AbsDir, snapshot: SnapshotAssertion, local_git_repo: GitDir
) -> None:
    remote = AbsDir(tempfile.mkdtemp())
    add_commit(remote, test_data_path / RelDir("remote"))
    diff = Diff.new_file(GitDir(remote), file)
    tmp_filepath = local_git_repo / file.target
    tmp_filepath.path.parent.mkdir(parents=True, exist_ok=True)
    current_path = test_data_path / RelDir("local") / file.target
    if current_path.exists():
        shutil.copy2(current_path, tmp_filepath)
    diff.apply(local_git_repo)
    with open(tmp_filepath) as f:
        assert f.read() == snapshot
