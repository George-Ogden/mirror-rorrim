from __future__ import annotations

from collections.abc import Generator
from multiprocessing import Process, Queue
from pathlib import Path
import random
import tempfile
import time

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
        pytest.param(
            # HTTPS remote
            "https://github.com/George-Ogden/dbg",
            ["_debug/__init__.py", "debug/__init__.py"],
            marks=[pytest.mark.slow],
        ),
        pytest.param(
            # SSH remote
            "git@github.com:George-Ogden/pytest-dbg.git",
            ["src/plugin.py"],
            marks=[pytest.mark.slow],
        ),
        local_remote_clone_test_case(),
    ],
)
def test_clone_remote(remote: str, expected_files: list[str], typed_tmp_path: AbsDir) -> None:
    GitHelper._clone(Remote(remote), typed_tmp_path)
    for file in expected_files:
        assert (typed_tmp_path / RelFile(file)).exists()


def update_already_up_to_date_repo_test_case() -> tuple[list[str], AbsDir]:
    local = tempfile.mkdtemp()
    remote = tempfile.mkdtemp()
    add_commit(remote, dict.fromkeys(["file1", "file2"]))
    git.Repo(remote).clone(local)
    return ["file1", "file2"], AbsDir(local)


def update_repository_linearly_behind_test_case() -> tuple[list[str], AbsDir]:
    local = tempfile.mkdtemp()
    remote = tempfile.mkdtemp()
    add_commit(remote, dict.fromkeys(["file1"]))
    git.Repo(remote).clone(local)
    add_commit(remote, dict.fromkeys(["file1", "file2"]))
    return ["file1", "file2"], AbsDir(local)


def update_repository_linearly_ahead_test_case() -> tuple[list[str], AbsDir]:
    local = tempfile.mkdtemp()
    remote = tempfile.mkdtemp()
    add_commit(remote, dict.fromkeys(["file1", "file2"]))
    git.Repo(remote).clone(local)
    add_commit(local, dict.fromkeys(["file1"]))
    return ["file1", "file2"], AbsDir(local)


def update_repository_out_of_sync_test_case() -> tuple[list[str], AbsDir]:
    local = tempfile.mkdtemp()
    remote = tempfile.mkdtemp()
    add_commit(remote, dict.fromkeys(["file1", "file2"]))
    git.Repo(remote).clone(local)
    add_commit(remote, dict.fromkeys(["file1", "file2", "file3"]))
    add_commit(local, dict.fromkeys(["file1"]))
    return ["file1", "file2", "file3"], AbsDir(local)


def update_repository_with_dirty_workdir_test_case() -> tuple[list[str], AbsDir]:
    local = tempfile.mkdtemp()
    remote = tempfile.mkdtemp()
    add_commit(remote, dict.fromkeys(["file1", "file2"]))
    git.Repo(remote).clone(local)
    (Path(local) / "file2").unlink()
    return ["file1", "file2"], AbsDir(local)


@pytest.mark.parametrize(
    "expected_files, folder",
    [
        update_already_up_to_date_repo_test_case(),
        update_repository_linearly_behind_test_case(),
        update_repository_linearly_ahead_test_case(),
        update_repository_out_of_sync_test_case(),
        update_repository_with_dirty_workdir_test_case(),
    ],
)
def test_sync(expected_files: list[str], folder: AbsDir) -> None:
    GitHelper._sync(folder)
    for file in expected_files:
        assert (folder / RelFile(file)).exists()


def commit_repeatedly(remote: AbsDir) -> None:
    i = 1
    while True:
        add_commit(remote, dict(file=i))
        i += 1
        time.sleep(0.01)


def write_commit_to_queue(remote: Remote, local: AbsDir, queue: Queue[str]) -> None:
    # Can clear cache because the lock is saved locally in test body.
    GitHelper.checkout.cache_clear()
    GitHelper.checkout(remote, local)
    with open(local / RelFile("file")) as f:
        print(f"follower value = {f.read()}")
    queue.put(GitHelper.commit(local))


@pytest.fixture
def updating_remote() -> Generator[Remote]:
    remote = Remote(tempfile.mkdtemp())
    add_commit(AbsDir(remote.repo), dict(file=0))
    committer = Process(target=commit_repeatedly, args=(remote,))
    committer.start()
    yield remote
    committer.kill()


@pytest.mark.slow
@pytest.mark.parametrize("seed", range(3))
def test_checkout_race_condition(
    typed_tmp_path: AbsDir, seed: int, updating_remote: Remote
) -> None:
    local = typed_tmp_path
    random.seed(seed)
    time.sleep(random.random())
    lock = GitHelper.checkout(updating_remote, local)
    assert lock.leader
    commit = GitHelper.commit(local)
    with open(local / RelFile("file")) as f:
        print(f"leader value = {f.read()}")
    time.sleep(random.random())
    queue: Queue[str] = Queue()
    follower = Process(target=write_commit_to_queue, args=(updating_remote, local, queue))
    follower.start()
    follower.join(1.0)
    assert queue.get_nowait() == commit
