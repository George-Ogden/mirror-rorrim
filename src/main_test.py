from collections.abc import Callable
import shlex
import shutil

from inline_snapshot import snapshot
import pytest
from pytest import CaptureFixture

from .constants import MIRROR_LOCK, MIRROR_NAME
from .main import main
from .test_utils import add_commit, normalize_message
from .typed_path import AbsDir, GitDir, RelDir, RelFile

CWD = AbsDir.cwd()


def remove_git_data(local: GitDir) -> None:
    shutil.rmtree(local / RelDir(".git"))


def add_existing_lock_test_case(local: AbsDir) -> None:
    (local / MIRROR_LOCK).path.touch()


def all_up_to_date_test_case(local: GitDir) -> None:
    add_commit(local, CWD / RelDir("test_data/checker_tests/up_to_date"))


@pytest.mark.parametrize(
    "args, expected, setup_repo",
    [
        # install tests
        (
            # abs path to config
            f"install --config {CWD / RelFile('test_data/installer_tests/empty_repo_with_config/.mirror.yaml')}",
            None,
            None,
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
            add_existing_lock_test_case,
        ),
        # check tests
        (
            # works fine
            "check",
            None,
            all_up_to_date_test_case,
        ),
        (
            # not a git repo
            "check",
            snapshot(
                "InvalidGitRepositoryError: 'GIT_DIR' is not a git repository, please run `git init` before installing."
            ),
            remove_git_data,
        ),
    ],
)
def test_main(
    args: str,
    expected: str | None,
    setup_repo: Callable[[GitDir], None] | None,
    local_git_repo: GitDir,
    capsys: CaptureFixture,
) -> None:
    if setup_repo is not None:
        setup_repo(local_git_repo)
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
