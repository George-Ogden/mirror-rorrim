from collections.abc import Callable
import os
import tempfile

from inline_snapshot import snapshot
import pytest
from pytest import LogCaptureFixture
from syrupy.assertion import SnapshotAssertion

from .config_parser import Parser
from .constants import MIRROR_LOCK
from .mirror import Mirror
from .state import MirrorState
from .test_utils import add_commit, normalize_message, quick_mirror, quick_mirror_repo
from .typed_path import AbsDir, RelDir, RelFile
from .types import ExitCode


@pytest.fixture
def test_data_path(global_test_data_path: AbsDir) -> AbsDir:
    return global_test_data_path / RelDir("mirror_tests")


@pytest.mark.parametrize(
    "config_name, expected",
    [
        (
            "single",
            quick_mirror(
                [quick_mirror_repo("https://github.com/George-Ogden/dbg", ["pyproject.toml"])]
            ),
        ),
        (
            "multiple",
            quick_mirror(
                [
                    quick_mirror_repo(
                        "https://github.com/George-Ogden/mypy-pytest",
                        ["pyproject.toml", ("requirements-dev.txt", "requirements.txt")],
                    ),
                    quick_mirror_repo(
                        "git@github.com:George-Ogden/actions.git",
                        [
                            (
                                ".github/workflows/python-release.yaml",
                                ".github/workflows/release.yaml",
                            ),
                            (
                                ".github/workflows/python-test.yaml",
                                ".github/workflows/test.yaml",
                            ),
                            (
                                ".github/workflows/lint.yaml",
                                ".github/workflows/lint.yaml",
                            ),
                        ],
                    ),
                ]
            ),
        ),
        (
            "trivial_state",
            quick_mirror(
                [
                    quick_mirror_repo(
                        "https://github.com/George-Ogden/mypy-pytest",
                        ["pyproject.toml", ("requirements-dev.txt", "requirements.txt")],
                    ),
                ]
            ),
        ),
        (
            "complex_state",
            quick_mirror(
                [
                    quick_mirror_repo(
                        "https://github.com/George-Ogden/mypy-pytest",
                        ["pyproject.toml", ("requirements-dev.txt", "requirements.txt")],
                    ),
                    quick_mirror_repo(
                        "git@github.com:George-Ogden/actions.git",
                        [
                            (
                                ".github/workflows/python-release.yaml",
                                ".github/workflows/release.yaml",
                                "abc123",
                            ),
                            (
                                ".github/workflows/python-test.yaml",
                                ".github/workflows/test.yaml",
                                "abc123",
                            ),
                            (
                                ".github/workflows/lint.yaml",
                                ".github/workflows/lint.yaml",
                            ),
                        ],
                    ),
                ]
            ),
        ),
    ],
)
def test_mirror_from_config(
    config_name: str, expected: Mirror, global_test_data_path: AbsDir
) -> None:
    config_dir = global_test_data_path / RelDir("config_tests")
    config_path = config_dir / RelFile(f"{config_name}.config.yaml")
    state_path = config_dir / RelFile(f"{config_name}.state.yaml")
    config = Parser.parse_file(config_path)
    if os.path.exists(state_path):
        with open(state_path) as f:
            state = MirrorState.load(f)
    else:
        state = None
    assert Mirror.from_config(config, state) == expected


def multiple_repos_local_test_case() -> Mirror:
    remote1 = tempfile.mkdtemp()
    remote2 = tempfile.mkdtemp()
    commit1 = add_commit(remote1, dict(file1="file1", file2="file2"))
    commit2 = add_commit(remote2, dict(file3="file3", file4="file4", file5="file5"))
    mirror = quick_mirror(
        [
            quick_mirror_repo(remote1, ["file1", "file2", ("file2", "file3")]),
            quick_mirror_repo(remote2, ["file4", "file5", ("file3", "file6")]),
        ]
    )
    object.__setattr__(
        mirror,
        "__replacement__",
        {remote1: "remote1", remote2: "remote2", commit1.sha: "commit1", commit2.sha: "commit2"},
    )
    return mirror


@pytest.mark.parametrize(
    "mirror, test_name",
    [
        (
            quick_mirror(
                [quick_mirror_repo("https://github.com/George-Ogden/dbg", ["pyproject.toml"])]
            ),
            "single",
        ),
        (multiple_repos_local_test_case(), multiple_repos_local_test_case.__name__),
    ],
)
def test_mirror_state(mirror: Mirror, snapshot: SnapshotAssertion, typed_tmp_path: AbsDir) -> None:
    mirror.checkout_all()
    with open(typed_tmp_path / RelFile(MIRROR_LOCK), "a+") as f:
        mirror.state.dump(f)
        f.seek(0)
        contents = f.read()
        if hasattr(mirror, "__replacement__"):
            for search, replacement in mirror.__replacement__.items():
                contents = contents.replace(search, replacement)
        assert contents == snapshot


def all_up_to_date_test_case() -> Mirror:
    repo1 = tempfile.mkdtemp()
    repo2 = tempfile.mkdtemp()
    add_commit(repo1, dict(file1="file1"))
    commit1 = add_commit(repo1, dict(file2="file2"))
    commit2 = add_commit(repo2, dict(file3="file3", file4="file4"))
    return quick_mirror(
        [
            quick_mirror_repo(repo1, [("file1", "file2", commit1)]),
            quick_mirror_repo(repo2, [("file3", commit2), ("file4", "file5", commit2)]),
        ]
    )


def partially_up_to_date_test_case() -> Mirror:
    repo1 = tempfile.mkdtemp()
    repo2 = tempfile.mkdtemp()
    commit1 = add_commit(repo1, dict(file1="file1"))
    add_commit(repo1, dict(file1="deleted", file2="file2"))
    commit2 = add_commit(repo2, dict(file3="file3", file4="file4", file5="file5"))
    return quick_mirror(
        [
            quick_mirror_repo(repo1, [("file1", commit1), ("file2", commit1)]),
            quick_mirror_repo(repo2, [("file3", commit2), ("file4", commit2), "file5"]),
        ]
    )


def none_up_to_date_test_case() -> Mirror:
    repo1 = tempfile.mkdtemp()
    repo2 = tempfile.mkdtemp()
    repo3 = tempfile.mkdtemp()
    commit1 = add_commit(repo1, dict(file1="file1"))
    add_commit(repo1, dict(file2="file2"))
    add_commit(repo2, dict(file3="file3"))
    commit3 = add_commit(repo3, dict(file4="file4"))
    add_commit(repo3, dict(file4="file4.1", file5="file5"))
    return quick_mirror(
        [
            quick_mirror_repo(repo1, [("file1", "file2", commit1)]),
            quick_mirror_repo(repo2, ["file3"]),
            quick_mirror_repo(repo3, [("file4", commit3), "file5"]),
        ]
    )


@pytest.mark.parametrize("log_level", ["INFO"])
@pytest.mark.parametrize(
    "setup, expected_message, expected_exitcode",
    [
        (
            all_up_to_date_test_case,
            snapshot(
                "Checking out all repos ...    Checking out all repos [done]    All up to date!"
            ),
            0,
        ),
        (
            partially_up_to_date_test_case,
            snapshot(
                "Checking out all repos ...    Checking out all repos [done]    'file1' has commit Commit 1, but 'GIT_DIR' has commit Commit 2.    'file2' has commit Commit 1, but 'GIT_DIR' has commit Commit 2.    'file5' has not been mirrored from 'GIT_DIR'."
            ),
            1,
        ),
        (
            none_up_to_date_test_case,
            snapshot(
                "Checking out all repos ...    Checking out all repos [done]    'file1' has commit Commit 1, but 'GIT_DIR' has commit Commit 2.    'file3' has not been mirrored from 'GIT_DIR'.    'file4' has commit Commit 1, but 'GIT_DIR' has commit Commit 2.    'file5' has not been mirrored from 'GIT_DIR'."
            ),
            1,
        ),
    ],
)
def test_mirror_check(
    setup: Callable[[], Mirror],
    expected_message: str,
    expected_exitcode: ExitCode,
    caplog: LogCaptureFixture,
    log_cleanly: None,
) -> None:
    mirror = setup()
    exitcode = mirror.check()
    assert exitcode == expected_exitcode
    log_message = normalize_message(
        caplog.text.strip(), git_dir=[AbsDir(repo.source.repo) for repo in mirror]
    )
    assert log_message == expected_message
