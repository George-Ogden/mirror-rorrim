from inline_snapshot import snapshot
import pytest
from syrupy.assertion import SnapshotAssertion

from .checker import MirrorChecker
from .main import check_for_errors
from .test_utils import normalize_message, setup_repo, snapshot_of_repo
from .typed_path import AbsDir, GitDir, RelDir


@pytest.fixture
def test_data_path(global_test_data_path: AbsDir) -> AbsDir:
    return global_test_data_path / RelDir("checker_tests")


def quick_checker(target: None | str | AbsDir) -> MirrorChecker:
    return MirrorChecker(GitDir(target or AbsDir.cwd()))


@pytest.mark.parametrize("log_level", ["INFO"])
@pytest.mark.parametrize(
    "test_name, exitcode, expected_log",
    [
        (
            "up_to_date",
            0,
            snapshot(
                "Checking out all repos ...    Checking out all repos [done]    All up to date!"
            ),
        ),
        pytest.param(
            "behind",
            1,
            snapshot(
                "Checking out all repos ...    Checking out all repos [done]    'config-only.yaml' has commit 84b0856, but 'https://github.com/George-Ogden/remote-installer-test-data' has commit 446d376."
            ),
            marks=[pytest.mark.slow],
        ),
        (
            "missing_config",
            1,
            snapshot(
                "Parsing config [failed]    FileNotFoundError: [Errno 2] No such file or directory: 'GIT_DIR/.mirror.yaml'"
            ),
        ),
        (
            "missing_lock",
            1,
            snapshot(
                "FileNotFoundError: GIT_DIR/.mirror.lock - have you installed Mirror|rorriM yet? If not, install it first."
            ),
        ),
        (
            "untracked_file",
            1,
            snapshot(
                "Checking out all repos ...    Checking out all repos [failed]    MissingFileError: 'filedoesnotexist' could not be found from 'https://github.com/George-Ogden/remote-installer-test-data'."
            ),
        ),
        (
            "invalid_commit",
            1,
            snapshot(
                "Checking out all repos ...    Checking out all repos [done]    'config-only.yaml' has commit 0000000, but 'https://github.com/George-Ogden/remote-installer-test-data' has commit 446d376."
            ),
        ),
        (
            "empty_lock",
            1,
            snapshot(
                "YAMLError: Error while loading 'GIT_DIR/.mirror.lock': unable to load data from lock file."
            ),
        ),
        (
            "duplicate_lock_source",
            1,
            snapshot(
                "RuntimeError: Error while loading 'GIT_DIR/.mirror.lock'. (ValueError: Expected all sources to be unique.)"
            ),
        ),
    ],
)
def test_checker_check(
    test_name: str,
    exitcode: int,
    expected_log: str,
    local_git_repo: GitDir,
    test_data_path: AbsDir,
    snapshot: SnapshotAssertion,
    caplog: pytest.LogCaptureFixture,
    log_cleanly: None,
) -> None:
    checker = quick_checker(local_git_repo)
    setup_repo(local_git_repo, test_data_path / RelDir(test_name))

    with pytest.raises(SystemExit) as e:
        check_for_errors(checker.check)()
    assert e.value.code == exitcode
    assert normalize_message(caplog.text, git_dir=local_git_repo) == expected_log
    assert snapshot_of_repo(local_git_repo, include_lockfile=True) == snapshot
