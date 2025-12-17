from collections.abc import Callable, Generator, Sequence
import os
from pathlib import Path
import shutil
import tempfile
from unittest import mock

import git
from git import GitError
from inline_snapshot import snapshot
import pytest
from pytest import LogCaptureFixture
from syrupy.assertion import SnapshotAssertion

from .config import MirrorRepoConfig
from .config_parser_test import quick_mirror_repo_config
from .githelper import GitHelper
from .repo import MirrorRepo, MissingFileError
from .state import MirrorRepoState
from .test_utils import add_commit, normalize_message, quick_mirror_repo, quick_mirror_repo_state
from .typed_path import AbsDir, GitDir, RelDir, RelFile, Remote
from .types import Commit


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
        snapshot("'file2' could not be found from 'REMOTE'."),
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


def checkout_not_a_git_repo_test_case() -> tuple[
    Callable[[], MirrorRepo], tuple[type[GitError], str]
]:
    def setup_repo() -> MirrorRepo:
        remote = tempfile.mkdtemp()
        repo = quick_mirror_repo(remote, ["file"])
        (Path(remote) / "file").touch()
        return repo

    return setup_repo, (GitError, snapshot("Unable to checkout 'REMOTE'."))


@pytest.mark.parametrize(
    "setup_repo, error",
    [
        pytest.param(
            lambda: quick_mirror_repo("https://github.com/George-Ogden/actions/", ["version.txt"]),
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
        assert str(e.value).replace(repo.source.repo, "REMOTE") == error_msg
        assert str(e.value).endswith(".")


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
    repo: MirrorRepo, test_data_path: AbsDir, snapshot: SnapshotAssertion, local_git_repo: GitDir
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
    return MirrorRepoState(Remote(source), Commit(commit), sorted(RelFile(file) for file in files))


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


def all_up_to_date_test_case(git_dir: GitDir) -> MirrorRepo:
    commit = add_commit(git_dir, dict(file1="file1", file2="file2", file3="file3"))
    return quick_mirror_repo(git_dir, [("file1", commit), ("file2", "file3", commit)])


def empty_up_to_date_test_case(git_dir: GitDir) -> MirrorRepo:
    add_commit(git_dir)
    return quick_mirror_repo(git_dir, [])


def none_up_to_date_test_case(git_dir: GitDir) -> MirrorRepo:
    commit = add_commit(git_dir, dict(file1="file1", file2="file2", file3="file3"))
    add_commit(git_dir, dict(file2="file1", file3="file2", file4="file3"))
    return quick_mirror_repo(
        git_dir, [("file1", commit), ("file2", commit), ("file3", "file4", commit)]
    )


def all_but_missing_up_to_date_test_case(git_dir: GitDir) -> MirrorRepo:
    commit = add_commit(git_dir, dict(file1="file1", file2="file2", file3="file3"))
    return quick_mirror_repo(git_dir, [("file1", commit), ("file2", "file3", commit), "file4"])


@pytest.mark.parametrize("log_level", ["INFO"])
@pytest.mark.parametrize(
    "setup, expected_message",
    [
        (all_up_to_date_test_case, None),
        (empty_up_to_date_test_case, None),
        (
            none_up_to_date_test_case,
            snapshot(
                "'file1' has commit Commit 1, but 'GIT_DIR' has commit Commit 2.    'file2' has commit Commit 1, but 'GIT_DIR' has commit Commit 2.    'file3' has commit Commit 1, but 'GIT_DIR' has commit Commit 2."
            ),
        ),
        (
            all_but_missing_up_to_date_test_case,
            snapshot("'file4' has not been mirrored from 'GIT_DIR'."),
        ),
    ],
)
def test_all_up_to_date(
    setup: Callable[[GitDir], MirrorRepo],
    expected_message: None | str,
    local_git_repo: GitDir,
    caplog: LogCaptureFixture,
    log_cleanly: None,
) -> None:
    repo = setup(local_git_repo)
    GitHelper.checkout(repo.source, repo.cache)
    assert repo.all_up_to_date() == (expected_message is None)
    log_message = normalize_message(caplog.text, git_dir=local_git_repo)
    if expected_message is None:
        assert log_message == ""
    else:
        assert log_message == expected_message
        assert log_message.endswith(".")


@pytest.mark.parametrize(
    "config, state, expected",
    [
        # no state
        (
            quick_mirror_repo_config("sauce", ["file1", ("file2", "file3")]),
            None,
            quick_mirror_repo("sauce", ["file1", ("file2", "file3")]),
        ),
        # fully covering state
        (
            quick_mirror_repo_config("sauce", ["file1", ("file2", "file3")]),
            quick_mirror_repo_state("sauce", "commitabcdef", ["file1", "file2", "file3"]),
            quick_mirror_repo(
                "sauce", [("file1", Commit("commitabcdef")), ("file2", "file3", "commitabcdef")]
            ),
        ),
        # partially covering state
        (
            quick_mirror_repo_config("sauce", ["file1", ("file2", "file3")]),
            quick_mirror_repo_state("sauce", "commitabcdef", ["file1", "file3"]),
            quick_mirror_repo("sauce", [("file1", Commit("commitabcdef")), ("file2", "file3")]),
        ),
        # different canonical paths
        (
            quick_mirror_repo_config("https://myrepo.com/", ["file1", "file2"]),
            quick_mirror_repo_state("https://myrepo.com", "abc123", ["file1", "file3"]),
            quick_mirror_repo("https://myrepo.com/", [("file1", Commit("abc123")), ("file2")]),
        ),
    ],
)
def test_repo_from_config(
    config: MirrorRepoConfig, state: MirrorRepoState | None, expected: MirrorRepo
) -> None:
    assert MirrorRepo.from_config(config, state) == expected
