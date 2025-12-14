import functools
import os
import shutil
from subprocess import PIPE
import traceback
from typing import Any

import git
from git import GitCommandError, GitError, InvalidGitRepositoryError, Tree
from git import Repo as GitRepo
from git.cmd import _AutoInterrupt as AutoInterrupt
from loguru import logger

from .constants import MIRROR_MONITOR_EXTENSION, MIRROR_SEMAPHORE_EXTENSION
from .lock import FileSystemSemaphore
from .logger import describe
from .typed_path import AbsDir, GitDir, RelFile, Remote
from .types import Commit


class GitHelper:
    @classmethod
    @functools.cache
    def repo(cls, local: GitDir) -> GitRepo:
        # Convert to string explicitly to gitpython-developers/GitPython#2085
        return GitRepo(os.fspath(local))

    @classmethod
    def run_command(cls, local: GitDir, command: str, *args: Any, **kwargs: Any) -> Any:
        return getattr(cls.repo(local).git, command)(*args, **kwargs)

    @classmethod
    @functools.cache
    def checkout(cls, remote: Remote, local: GitDir) -> FileSystemSemaphore:
        semaphore = FileSystemSemaphore.acquire(local + MIRROR_SEMAPHORE_EXTENSION)
        if semaphore.leader:
            cls._checkout(remote, local)
        semaphore.synchronize(local + MIRROR_MONITOR_EXTENSION)
        # semaphore is cached to prevent destruction until exit
        return semaphore

    @classmethod
    def _checkout(cls, remote: Remote, local: GitDir) -> None:
        try:
            cls._clone(remote, local)
        except GitCommandError as e:
            logger.debug(e)
            try:
                try:
                    cls._sync(local)
                except InvalidGitRepositoryError as e:
                    logger.debug(e)
                    shutil.rmtree(local, ignore_errors=True)
                    cls._clone(remote, local)
            except Exception as e:
                traceback.print_exc()
                logger.debug(e)
                raise GitError(f"Unable to checkout {remote}.") from None

    @classmethod
    def _clone(cls, remote: Remote, local: AbsDir) -> None:
        with describe(f"Cloning {remote} into {local}", error_level="DEBUG"):
            GitRepo.clone_from(remote.canonical, os.fspath(local))

    @classmethod
    def _sync(cls, local: GitDir) -> None:
        with describe(f"Pulling {cls.repo(local).remote().url} into {local}", error_level="DEBUG"):
            repo = cls.repo(local)
            [fetch_info] = repo.remote().fetch()
            repo.head.reset(fetch_info.commit, working_tree=True, index=True)

    @classmethod
    def fresh_diff(cls, local: GitDir, file: RelFile) -> str:
        cmd: AutoInterrupt = cls.run_command(
            local,
            "diff",
            "--no-index",
            "--full-index",
            "--",
            os.devnull,
            os.fspath(file),
            as_process=True,
        )
        assert cmd.proc is not None
        assert cmd.proc.stdout is not None
        _ret_code = cmd.proc.wait()
        return git.safe_decode(cmd.proc.stdout.read())

    @classmethod
    def file_diff(cls, local: GitDir, commit: Commit, file: RelFile) -> str:
        cmd: AutoInterrupt = cls.run_command(
            local,
            "diff",
            "--full-index",
            str(commit),
            "--",
            os.fspath(file),
            as_process=True,
        )
        assert cmd.proc is not None
        assert cmd.proc.stdout is not None
        _ret_code = cmd.proc.wait()
        return git.safe_decode(cmd.proc.stdout.read())

    @classmethod
    def file_blob(cls, local: GitDir, commit: Commit, file: RelFile) -> bytes:
        # gitpython-developers/GitPython#2094
        blob = cls.tree(local, commit) / os.fspath(file)
        return blob.data_stream.read()

    @classmethod
    def add(cls, local: GitDir, *files: RelFile) -> None:
        # repo.index.add is not syncing
        cls.run_command(local, "add", *(os.fspath(file) for file in files))

    @classmethod
    def apply_patch(cls, local: GitDir, patch: str) -> None:
        cmd: AutoInterrupt = cls.run_command(
            local, "apply", "--allow-empty", "-3", "-", istream=PIPE, as_process=True
        )
        assert cmd.proc is not None
        assert cmd.proc.stdin is not None
        cmd.proc.stdin.write(patch.encode("utf-8"))
        cmd.proc.stdin.close()
        _ret_code = cmd.proc.wait()

    @classmethod
    def commit(cls, local: GitDir) -> str:
        return cls.repo(local).head.commit.hexsha

    @classmethod
    def tree(cls, local: GitDir, commit: Commit | None = None) -> Tree:
        return cls.repo(local).tree(None if commit is None else str(commit))
