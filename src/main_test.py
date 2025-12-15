from collections.abc import Callable
import shlex
import shutil

from inline_snapshot import snapshot
import pytest
from pytest import CaptureFixture

from .constants import MIRROR_LOCK, MIRROR_NAME
from .main import main
from .test_utils import add_commit, normalize_message
from .typed_path import AbsDir, GitDir, RelDir


@pytest.fixture
def test_data_path(global_test_data_path: AbsDir) -> AbsDir:
    return global_test_data_path


def remove_git_data(local: GitDir) -> None:
    shutil.rmtree(local / RelDir(".git"))


@pytest.mark.parametrize(
    "args, expected, setup_repo",
    [
        # install tests
        (
            # abs path to config
            "install --config .mirror.yaml",
            None,
            "installer_tests/empty_repo_with_config",
        ),
        (
            # config is missing
            "install --config-repo https://github.com/George-Ogden/concurrent-algorithms",
            snapshot(
                "Syncing all repos [failed]    MissingFileError: '.mirror.yaml' could not be found from 'https://github.com/George-Ogden/concurrent-algorithms'."
            ),
            None,
        ),
        (
            # config is a folder
            "install --config-repo https://github.com/George-Ogden/dbg --config test_data",
            snapshot(
                "Syncing all repos [failed]    IsADirectoryError: 'test_data' from 'https://github.com/George-Ogden/dbg' is a directory."
            ),
            None,
        ),
        (
            # not a local repo
            "install --config-repo https://github.com/George-Ogden/mirror-rorrim-test-data --config-file config-only.yaml",
            snapshot(
                "InvalidGitRepositoryError: 'GIT_DIR' is not a git repository, please run `git init` before installing."
            ),
            remove_git_data,
        ),
        (
            # abs path + remote (valid)
            "install --config-repo https://github.com/George-Ogden/mirror-rorrim-test-data/ --config-file /config-only.yaml",
            None,
            None,
        ),
        (
            # abs path + remote (invalid)
            "install --config-repo https://github.com/George-Ogden/mirror-rorrim-test-data/ --config-file /.mirror.yaml",
            snapshot(
                "Syncing all repos [failed]    MissingFileError: '.mirror.yaml' could not be found from 'https://github.com/George-Ogden/mirror-rorrim-test-data/'."
            ),
            None,
        ),
        (
            # invalid config
            "install --config-repo https://github.com/George-Ogden/dbg --config-file requirements.txt",
            snapshot(
                "Parsing config [failed]    Syncing all repos [failed]    ParserError: An unexpected error occurred during parsing @ requirements.txt:1:1: expected mirror mapping, got string."
            ),
            None,
        ),
        (
            # not a local repo
            "install --config-repo https://github.com/George-Ogden/mirror-rorrim-test-data --config-file config-only.yaml",
            snapshot(
                "FileExistsError: GIT_DIR/.mirror.lock - have you already installed Mirror|rorriM? If not, delete this file and try again."
            ),
            "installer_tests/existing_lock",
        ),
        # check tests
        (
            # works fine
            "check",
            None,
            "checker_tests/up_to_date",
        ),
        (
            # not a git repo
            "check",
            snapshot(
                "InvalidGitRepositoryError: 'GIT_DIR' is not a git repository, please run `git init` before installing."
            ),
            remove_git_data,
        ),
        # sync tests
        (
            # works fine
            "sync",
            None,
            "syncer_tests/behind",
        ),
        (
            # not a git repo
            "sync",
            snapshot(
                "InvalidGitRepositoryError: 'GIT_DIR' is not a git repository, please run `git init` before installing."
            ),
            remove_git_data,
        ),
        (
            # commit does not exist
            "sync",
            snapshot(
                "Updating all files [failed]    RuntimeError: Unable to calculate diff from 0000000000000000000000000000000000000000 for '.pre-commit-config.yaml' (from 'https://github.com/George-Ogden/remote-installer-test-data')."
            ),
            "syncer_tests/invalid_commit",
        ),
        (
            # file does not exist
            "sync",
            snapshot(
                "Checking out all repos [failed]    Syncing all repos [failed]    MissingFileError: 'filedoesnotexist' could not be found from 'https://github.com/George-Ogden/remote-installer-test-data'."
            ),
            "syncer_tests/untracked_file",
        ),
    ],
)
def test_main(
    args: str,
    expected: str | None,
    setup_repo: Callable[[GitDir], None] | str | RelDir | None,
    local_git_repo: GitDir,
    test_data_path: AbsDir,
    capsys: CaptureFixture,
) -> None:
    if callable(setup_repo):
        setup_repo(local_git_repo)
    elif setup_repo:
        add_commit(local_git_repo, test_data_path / RelDir(setup_repo))
    argv = ["-q", *shlex.split(args)]
    mirror_existed_before = (local_git_repo / MIRROR_LOCK).exists()
    with pytest.raises(SystemExit) as e:
        main.main(argv, prog_name=MIRROR_NAME)
    if expected is None:
        assert e.value.code == 0
        assert (local_git_repo / MIRROR_LOCK).exists()
    else:
        assert e.value.code != 0
        assert (local_git_repo / MIRROR_LOCK).exists() == mirror_existed_before
        out, _err = capsys.readouterr()
        assert normalize_message(out, git_dir=local_git_repo) == expected
