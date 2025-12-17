from __future__ import annotations

from collections.abc import Callable
import functools
import os
from pathlib import Path
import sys
import traceback

import click
from git import InvalidGitRepositoryError
from loguru import logger

from .checker import MirrorChecker
from .constants import MIRROR_FILE
from .githelper import GitHelper
from .installer import InstallSource, MirrorInstaller
from .logger import ProgramState, setup_logger
from .syncer import MirrorSyncer
from .typed_path import AbsDir, AbsFile, GitDir, RelFile, Remote
from .types import ExitCode


def check_for_errors[**P](fn: Callable[P, ExitCode | None]) -> Callable[P, None]:
    @functools.wraps(fn)
    def main(*args: P.args, **kwargs: P.kwargs) -> None:
        try:
            exitcode = fn(*args, **kwargs)
        except BaseException as e:
            logger.debug(f"Threw {type(e)}!")
            logger.trace(traceback.format_exc())
            logger.error(f"{type(e).__name__}: {e}")
            sys.exit(1)
        if exitcode is not None:
            sys.exit(exitcode)

    return main


@click.group(context_settings=dict(show_default=True))
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Display more output (repeat up to 2 times).",
    show_default=False,
)
@click.option(
    "-q",
    "--quiet",
    count=True,
    help="Display less output (repeat up to 3 times).",
    show_default=False,
)
@check_for_errors
def main(quiet: int, verbose: int) -> None:
    setup_logger(quiet, verbose)
    check_git_repo()


def check_git_repo() -> None:
    try:
        GitHelper.repo(AbsDir.cwd())
    except InvalidGitRepositoryError as e:
        raise InvalidGitRepositoryError(
            f"{AbsDir.cwd()} is not a git repository, please run `git init` before installing."
        ) from e


@main.command()
@click.option("--config-file", "--config", "-c", default=os.fspath(MIRROR_FILE))
@click.option("--config-repo", default=None)
@check_for_errors
@ProgramState.record_command
def install(config_file: str, config_repo: str | None) -> None:
    """Setup Mirror|rorriM for the first time in the current directory.

    \b
    Examples:
    # Install using local config.
    python main.py install

    \b
    # Install using the config from the remote repo.
    python main.py install ./mirror/ --config-repo https://myrepos.com/mirror

    \b
    # Install using the Python config from the remote repo.
    python main.py install --config-repo https://myrepos.com/mirror --config .python-mirror.yaml

    \b
    # Install using a local config.
    python main.py install --config /configs/mirror-config.yml
    """
    config_path = Path(config_file)
    source_path = AbsFile(config_path) if config_path.is_absolute() else RelFile(config_path)
    source_remote = None if config_repo is None else Remote(config_repo)
    if source_remote is None:
        source: InstallSource = source_path
    else:
        if isinstance(source_path, AbsFile):
            source_path = RelFile(source_path.path.relative_to("/"))
        source = (source_remote, source_path)
    installer = MirrorInstaller(target=GitDir.cwd(), source=source)
    installer.install()


@main.command()
@check_for_errors
@ProgramState.record_command
def check() -> ExitCode:
    """Check whether files from Mirror|rorriM are up to date with their remotes.

    \b
    Example:
    # Check the current directory.
    python main.py check
    """
    checker = MirrorChecker(target=GitDir.cwd())
    return checker.check()


@main.command()
@check_for_errors
@ProgramState.record_command
def sync() -> None:
    """Sync files from Mirror|rorriM with their remotes.

    \b
    Example:
    # Sync the current directory.
    python main.py sync
    """
    syncer = MirrorSyncer(target=GitDir.cwd())
    syncer.sync()
