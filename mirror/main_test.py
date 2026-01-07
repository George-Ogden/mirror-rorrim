from collections.abc import Callable
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

from inline_snapshot import snapshot
import pytest
from pytest import CaptureFixture

from .constants import MIRROR_LOCK, MIRROR_NAME
from .githelper import GitHelper
from .main import main
from .test_utils import add_commit, normalize_message, quick_installer
from .typed_path import AbsDir, GitDir, RelDir, RelFile


@pytest.fixture
def test_data_path(global_test_data_path: AbsDir) -> AbsDir:
    return global_test_data_path


def remove_git_data(local: GitDir) -> None:
    shutil.rmtree(local / RelDir(".git"))


@pytest.mark.parametrize(
    "args, exitcode ,logs, setup_repo",
    [
        # install tests
        (
            # abs path to config
            "install --config .mirror.yaml",
            0,
            snapshot(""),
            "installer_tests/empty_repo_with_config",
        ),
        (
            # config is missing
            "install --config-repo https://github.com/George-Ogden/concurrent-algorithms",
            1,
            snapshot(
                "Syncing all repos [failed]    MissingFileError: '.mirror.yaml' could not be found from 'https://github.com/George-Ogden/concurrent-algorithms'."
            ),
            None,
        ),
        (
            # config is a folder
            "install --config-repo https://github.com/George-Ogden/dbg --config test_data",
            1,
            snapshot(
                "Syncing all repos [failed]    IsADirectoryError: 'test_data' from 'https://github.com/George-Ogden/dbg' is a directory."
            ),
            None,
        ),
        (
            # not a local repo
            "install --config-repo https://github.com/George-Ogden/mirror-rorrim-test-data --config-file config-only.yaml",
            1,
            snapshot(
                "InvalidGitRepositoryError: 'GIT_DIR' is not a git repository, please run `git init` before installing."
            ),
            remove_git_data,
        ),
        (
            # abs path + remote (valid)
            "install --config-repo https://github.com/George-Ogden/mirror-rorrim-test-data/ --config-file /config-only.yaml",
            0,
            snapshot(""),
            None,
        ),
        (
            # abs path + remote (invalid)
            "install --config-repo https://github.com/George-Ogden/mirror-rorrim-test-data/ --config-file /.mirror.yaml",
            1,
            snapshot(
                "Syncing all repos [failed]    MissingFileError: '.mirror.yaml' could not be found from 'https://github.com/George-Ogden/mirror-rorrim-test-data/'."
            ),
            None,
        ),
        (
            # invalid config
            "install --config-repo https://github.com/George-Ogden/dbg --config-file requirements.txt",
            1,
            snapshot(
                "Parsing config [failed]    Syncing all repos [failed]    ParserError: An unexpected error occurred during parsing @ requirements.txt:1:1: expected mirror mapping, got string."
            ),
            None,
        ),
        (
            # not a local repo
            "install --config-repo https://github.com/George-Ogden/mirror-rorrim-test-data --config-file config-only.yaml",
            1,
            snapshot(
                "FileExistsError: GIT_DIR/.mirror.lock - have you already installed Mirror|rorriM? If not, delete this file and try again."
            ),
            "installer_tests/existing_lock",
        ),
        (
            # overwrite local mirror file
            "install -C https://github.com/George-Ogden/mirror-rorrim-test-data --config-file config-only.yaml",
            0,
            snapshot("'.mirror.yaml' has been overwritten during installation."),
            "installer_tests/remote_config_overwrite",
        ),
        (
            # overwrite local mirror file with itself
            "install",
            0,
            snapshot(""),
            "installer_tests/remote_config_overwrite",
        ),
        # check tests
        (
            # works fine
            "check",
            0,
            snapshot(""),
            "checker_tests/up_to_date",
        ),
        (
            # not a git repo
            "check",
            1,
            snapshot(
                "InvalidGitRepositoryError: 'GIT_DIR' is not a git repository, please run `git init` before installing."
            ),
            remove_git_data,
        ),
        (
            # behind with pre-commit
            "check --pre-commit",
            1,
            snapshot("Mirror|rorriM config files are not up to date; run `mirror sync` to update."),
            "checker_tests/behind",
        ),
        # sync tests
        (
            # works fine
            "sync",
            0,
            snapshot(""),
            "syncer_tests/behind",
        ),
        (
            # not a git repo
            "sync",
            1,
            snapshot(
                "InvalidGitRepositoryError: 'GIT_DIR' is not a git repository, please run `git init` before installing."
            ),
            remove_git_data,
        ),
        (
            # commit does not exist
            "sync",
            1,
            snapshot(
                "Updating all files [failed]    RuntimeError: Unable to calculate diff from 0000000 for '.pre-commit-config.yaml' (from 'https://github.com/George-Ogden/remote-installer-test-data')."
            ),
            "syncer_tests/invalid_commit",
        ),
        (
            # file does not exist
            "sync",
            1,
            snapshot(
                "Checking out all repos [failed]    Syncing all repos [failed]    MissingFileError: 'filedoesnotexist' could not be found from 'https://github.com/George-Ogden/remote-installer-test-data'."
            ),
            "syncer_tests/untracked_file",
        ),
        (
            # update mirror file
            "sync",
            0,
            snapshot(
                "'.mirror.yaml' modified while syncing. Please merge any conflicts then rerun to sync any added files."
            ),
            "syncer_tests/update_mirror",
        ),
    ],
)
def test_main(
    args: str,
    exitcode: int,
    logs: str,
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
    if exitcode == 0:
        assert e.value.code == 0
        assert (local_git_repo / MIRROR_LOCK).exists()
    else:
        assert e.value.code != 0
        assert (local_git_repo / MIRROR_LOCK).exists() == mirror_existed_before
    out, _err = capsys.readouterr()
    assert normalize_message(out, git_dir=local_git_repo) == logs


@pytest.mark.slow
def test_pre_commit_with_mirror(
    local_git_repo: GitDir, test_data_path: AbsDir, capfd: CaptureFixture
) -> None:
    with open(
        test_data_path / RelDir("pre_commit_tests") / RelFile(".pre-commit-config.yaml")
    ) as f:
        pre_commit_contents = f.read()
    pre_commit_contents = pre_commit_contents.replace(
        "CURRENT_REPO", os.fspath(Path(__file__).parent.parent.absolute())
    )
    add_commit(local_git_repo, {".pre-commit-config.yaml": pre_commit_contents})
    quick_installer(
        local_git_repo, ("https://github.com/George-Ogden/mirror-config", "python.mirror.yaml")
    ).install()
    subprocess.run(
        ["pre-commit", "install"],
        cwd=local_git_repo,
        check=True,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    with open(local_git_repo / RelFile(".pre-commit-config.yaml"), "w") as f:
        f.write(pre_commit_contents)
    GitHelper.run_command(
        local_git_repo, "config", "user.email", "github-actions[bot]@users.noreply.github.com"
    )
    GitHelper.run_command(local_git_repo, "config", "user.name", "github-actions[bot]")
    commit_result = GitHelper.run_command(local_git_repo, "commit", "-am", "Setup mirror")
    assert commit_result.returncode == 0
