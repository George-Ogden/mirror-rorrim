from pathlib import Path
import tempfile

import git
import pytest

from .githelper import GitHelper
from .test_utils import add_commit
from .typed_path import AbsDir, RelFile, Remote


def local_remote_clone_test_case() -> tuple[str, list[str]]:
    files = ["folder/file", "unusually_named.file"]
    path = tempfile.mkdtemp()
    add_commit(path, dict.fromkeys(files))
    return path, files


@pytest.mark.parametrize(
    "remote, expected_files",
    [
        (
            # HTTPS remote
            "https://github.com/George-Ogden/dbg",
            ["_debug/__init__.py", "debug/__init__.py"],
        ),
        (
            # SSH remote
            "git@github.com:George-Ogden/pytest-dbg.git",
            ["src/plugin.py"],
        ),
        local_remote_clone_test_case(),
    ],
)
def test_clone_remote(remote: str, expected_files: list[str], typed_tmp_path: AbsDir) -> None:
    GitHelper.clone(Remote(remote), typed_tmp_path)
    for file in expected_files:
        assert (typed_tmp_path / RelFile(file)).exists()


def update_already_up_to_date_repo_test_case() -> tuple[Remote, list[str], AbsDir]:
    local = tempfile.mkdtemp()
    remote = tempfile.mkdtemp()
    add_commit(remote, dict.fromkeys(["file1", "file2"]))
    git.Repo(remote).clone(local)
    return Remote(remote), ["file1", "file2"], AbsDir(local)


def update_repository_linearly_behind_test_case() -> tuple[Remote, list[str], AbsDir]:
    local = tempfile.mkdtemp()
    remote = tempfile.mkdtemp()
    add_commit(remote, dict.fromkeys(["file1"]))
    git.Repo(remote).clone(local)
    add_commit(remote, dict.fromkeys(["file1", "file2"]))
    return Remote(remote), ["file1", "file2"], AbsDir(local)


def update_repository_linearly_ahead_test_case() -> tuple[Remote, list[str], AbsDir]:
    local = tempfile.mkdtemp()
    remote = tempfile.mkdtemp()
    add_commit(remote, dict.fromkeys(["file1", "file2"]))
    git.Repo(remote).clone(local)
    add_commit(local, dict.fromkeys(["file1"]))
    return Remote(remote), ["file1", "file2"], AbsDir(local)


def update_repository_out_of_sync_test_case() -> tuple[Remote, list[str], AbsDir]:
    local = tempfile.mkdtemp()
    remote = tempfile.mkdtemp()
    add_commit(remote, dict.fromkeys(["file1", "file2"]))
    git.Repo(remote).clone(local)
    add_commit(remote, dict.fromkeys(["file1", "file2", "file3"]))
    add_commit(local, dict.fromkeys(["file1"]))
    return Remote(remote), ["file1", "file2", "file3"], AbsDir(local)


def update_repository_with_dirty_workdir_test_case() -> tuple[Remote, list[str], AbsDir]:
    local = tempfile.mkdtemp()
    remote = tempfile.mkdtemp()
    add_commit(remote, dict.fromkeys(["file1", "file2"]))
    git.Repo(remote).clone(local)
    (Path(local) / "file2").unlink()
    return Remote(remote), ["file1", "file2"], AbsDir(local)


@pytest.mark.parametrize(
    "remote, expected_files, folder",
    [
        update_already_up_to_date_repo_test_case(),
        update_repository_linearly_behind_test_case(),
        update_repository_linearly_ahead_test_case(),
        update_repository_out_of_sync_test_case(),
        update_repository_with_dirty_workdir_test_case(),
    ],
)
def test_sync(remote: Remote, expected_files: list[str], folder: AbsDir) -> None:
    GitHelper.sync(remote, folder)
    for file in expected_files:
        assert (folder / RelFile(file)).exists()
