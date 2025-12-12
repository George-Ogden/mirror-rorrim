from collections.abc import Callable
import os
import shlex
import shutil

from inline_snapshot import snapshot
import pytest
from pytest import CaptureFixture

from .constants import MIRROR_LOCK, MIRROR_NAME
from .main import main
from .typed_path import AbsDir, GitDir, RelDir, RelFile


def remove_git_data(local: GitDir) -> None:
    shutil.rmtree(local / RelDir(".git"))


def add_lock(local: AbsDir) -> None:
    (local / MIRROR_LOCK).path.touch()


@pytest.mark.parametrize(
    "args, expected, setup_repo",
    [
        (
            # abs path to config
            f"install --config {AbsDir.cwd() / RelFile('test_data/installer_tests/empty_repo_with_config/.mirror.yaml')}",
            None,
            None,
        ),
        (
            # config is missing
            "install --config-repo https://github.com/George-Ogden/concurrent-algorithms",
            snapshot(
                "Syncing all repos [failed]\tMissingFileError: '.mirror.yaml' could not be found from 'https://github.com/George-Ogden/concurrent-algorithms'."
            ),
            None,
        ),
        (
            # config is a folder
            "install --config-repo https://github.com/George-Ogden/dbg --config test_data",
            snapshot(
                "Syncing all repos [failed]\tIsADirectoryError: 'test_data' from 'https://github.com/George-Ogden/dbg' is a directory."
            ),
            None,
        ),
        (
            # not a local repo
            "install --config-repo https://github.com/George-Ogden/remote-installer-test-data --config-file config-only.yaml",
            snapshot(
                "InvalidGitRepositoryError: 'LOCAL_GIT_REPO' is not a git repository, please run `git init` before installing."
            ),
            remove_git_data,
        ),
        (
            # abs path + remote (valid)
            "install --config-repo https://github.com/George-Ogden/remote-installer-test-data/ --config-file /config-only.yaml",
            None,
            None,
        ),
        (
            # abs path + remote (invalid)
            "install --config-repo https://github.com/George-Ogden/remote-installer-test-data/ --config-file /.mirror.yaml",
            snapshot(
                "Syncing all repos [failed]\tMissingFileError: '.mirror.yaml' could not be found from 'https://github.com/George-Ogden/remote-installer-test-data/'."
            ),
            None,
        ),
        (
            # invalid config
            "install --config-repo https://github.com/George-Ogden/dbg --config-file requirements.txt",
            snapshot(
                "Parsing config [failed]\tSyncing all repos [failed]\tParserError: An unexpected error occurred during parsing @ requirements.txt:1:1: expected mirror mapping, got string."
            ),
            None,
        ),
        (
            # not a local repo
            "install --config-repo https://github.com/George-Ogden/remote-installer-test-data --config-file config-only.yaml",
            snapshot(
                "FileExistsError: LOCAL_GIT_REPO/.mirror.lock - have you already installed Mirror|rorriM? If not, delete this file and try again."
            ),
            add_lock,
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
        assert (
            out.replace(os.fspath(local_git_repo), "LOCAL_GIT_REPO").replace("\n", "\t").strip()
            == expected
        )
