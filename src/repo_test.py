from collections.abc import Callable, Generator, Sequence
import os
import shutil
import tempfile
from unittest import mock

import git
from inline_snapshot import snapshot
import pytest
from syrupy.assertion import SnapshotAssertion

from .githelper import GitHelper
from .repo import MirrorRepo, MissingFileError
from .state import MirrorRepoState
from .test_utils import add_commit, quick_mirror_repo
from .typed_path import AbsDir, RelDir, RelFile, Remote


@pytest.fixture
def test_data_path(global_test_data_path: AbsDir) -> AbsDir:
    return global_test_data_path / RelDir("repo_tests")


@pytest.fixture
def mocked_cache_dir(typed_tmp_path: AbsDir) -> Generator[AbsDir]:
    with mock.patch("src.repo.MIRROR_CACHE", typed_tmp_path):
        yield typed_tmp_path


def checkout_with_missing_file_test_case() -> tuple[
    Callable[[], MirrorRepo], tuple[type[MissingFileError], str]
]:
    remote = tempfile.mkdtemp()
    add_commit(remote, dict.fromkeys(["file1", "file3"]))
    return lambda: quick_mirror_repo(remote, ["file1", ("file2", "file3")]), (
        MissingFileError,
        snapshot(),
    )


def checkout_not_behind_repository_test_case() -> tuple[Callable[[], MirrorRepo], None]:
    def setup_repo() -> MirrorRepo:
        remote = tempfile.mkdtemp()
        add_commit(remote, dict.fromkeys(["file1"]))
        repo = quick_mirror_repo(remote, ["file1", "file2"])
        GitHelper._clone(repo.source, repo.cache)
        add_commit(remote, dict.fromkeys(["file1", "file2"]))
        return repo

    return setup_repo, None


def checkout_not_a_git_repo_test_case() -> tuple[Callable[[], MirrorRepo], None]:
    def setup_repo() -> MirrorRepo:
        remote = tempfile.mkdtemp()
        add_commit(remote, dict.fromkeys(["file1"]))
        repo = quick_mirror_repo(remote, ["file1"])
        repo.cache.path.mkdir()
        (repo.cache.path / "file").touch()
        return repo

    return setup_repo, None


@pytest.mark.parametrize(
    "setup_repo, error",
    [
        pytest.param(
            lambda: quick_mirror_repo(
                "https://github.com/George-Ogden/actions/",
                ["version.txt"],
            ),
            None,
            marks=[pytest.mark.slow],
        ),
        checkout_with_missing_file_test_case(),
        pytest.param(*checkout_not_behind_repository_test_case(), marks=[pytest.mark.slow]),
        checkout_not_a_git_repo_test_case(),
    ],
)
def test_checkout(
    mocked_cache_dir: AbsDir,
    setup_repo: Callable[[], MirrorRepo],
    error: None | tuple[type[Exception], str],
) -> None:
    # Use callable to get access to the mocked cache dir.
    repo = setup_repo()
    if error is None:
        repo.checkout()
    else:
        error_type, error_msg = error
        with pytest.raises(error_type) as e:
            repo.checkout()
        error_msg = str(e.value)
        assert error_msg == error_msg
        assert error_msg.endswith(".")


@pytest.fixture
def test_name(repo: MirrorRepo) -> str:
    return repo.source.repo


def empty_repo_copy_one_file_test_case() -> MirrorRepo:
    return quick_mirror_repo("one_file", ["file"])


def non_empty_repo_copy_files_without_renaming_test_case() -> MirrorRepo:
    repo = quick_mirror_repo("no_renaming", ["identical", "conflict", "empty", "file"])
    return repo


def repo_renaming_test_case() -> MirrorRepo:
    return quick_mirror_repo(
        "renaming",
        [
            "identical",
            ("file", "new"),
            ("conflict", "exists"),
            ("empty", "empty-new"),
            ("file", "empty"),
        ],
    )


@pytest.mark.parametrize(
    "repo",
    [
        empty_repo_copy_one_file_test_case(),
        non_empty_repo_copy_files_without_renaming_test_case(),
        repo_renaming_test_case(),
    ],
)
def test_update_all(
    repo: MirrorRepo, test_data_path: AbsDir, snapshot: SnapshotAssertion, local_git_repo: AbsDir
) -> None:
    for file in repo.files:
        existing_file = test_data_path / RelDir("local") / file.target
        if existing_file.exists():
            shutil.copy2(existing_file, local_git_repo)
    # gitpython-developers/GitPython#2085
    git.Repo.init(os.fspath(repo.cache))
    shutil.copytree(test_data_path / RelDir("remote"), repo.cache, dirs_exist_ok=True)
    repo.update(local_git_repo)

    repo_contents = {}
    for _, _, filenames in local_git_repo.path.walk():
        for filename in filenames:
            with open(local_git_repo / RelFile(filename)) as f:
                repo_contents[filename] = f.read()
        break
    assert repo_contents == snapshot


def quick_repo_state(source: str, commit: str, files: Sequence[str]) -> MirrorRepoState:
    return MirrorRepoState(Remote(source), commit, sorted(RelFile(file) for file in files))


def local_repo_state_test_case() -> tuple[MirrorRepo, MirrorRepoState]:
    repo_dir = tempfile.mkdtemp()
    add_commit(repo_dir, dict(file1="file1", file2="file2", file3="file3"))
    commit = git.Repo(repo_dir).git.log(n=1, format="%H")
    return quick_mirror_repo(repo_dir, ["file1", ("file2", "file3")]), quick_repo_state(
        repo_dir, snapshot(commit), ["file1", "file2"]
    )


def repeated_file_test_case() -> tuple[MirrorRepo, MirrorRepoState]:
    repo_dir = tempfile.mkdtemp()
    add_commit(repo_dir, dict(file1="file1"))
    commit = git.Repo(repo_dir).git.log(n=1, format="%H")
    return quick_mirror_repo(repo_dir, ["file1", ("file1", "file2")]), quick_repo_state(
        repo_dir, snapshot(commit), ["file1"]
    )


@pytest.mark.parametrize(
    "repo, expected_state",
    [
        pytest.param(
            quick_mirror_repo(
                "https://github.com/George-Ogden/concurrent-language",
                [("Grammar.g4", "grammar.antlr"), "Makefile"],
            ),
            quick_repo_state(
                "https://github.com/George-Ogden/concurrent-language",
                "3d47e3072dbdaf9137ea817d8be1f9639dd375de",
                ["Grammar.g4", "Makefile"],
            ),
            marks=[pytest.mark.slow],
        ),
        local_repo_state_test_case(),
        repeated_file_test_case(),
    ],
)
def test_repo_state(repo: MirrorRepo, expected_state: MirrorRepoState) -> None:
    repo.checkout()
    assert repo.state == expected_state
