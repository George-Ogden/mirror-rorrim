import functools
import os
import shutil
from subprocess import PIPE
from typing import Any

import git
from git import Repo as GitRepo
from git.cmd import _AutoInterrupt as AutoInterrupt

from .constants import MIRROR_MONITOR_EXTENSION, MIRROR_SEMAPHORE_EXTENSION
from .lock import FileSystemSemaphore
from .logger import describe
from .typed_path import AbsDir, RelFile, Remote


class GitHelper:
    @classmethod
    @functools.cache
    def repo(cls, local: AbsDir) -> GitRepo:
        # Convert to string explicitly to gitpython-developers/GitPython#2085
        return GitRepo(os.fspath(local))

    @classmethod
    def run_command(cls, local: AbsDir, command: str, *args: Any, **kwargs: Any) -> Any:
        return getattr(cls.repo(local).git, command)(*args, **kwargs)

    @classmethod
    @functools.cache
    def checkout(cls, remote: Remote, local: AbsDir) -> FileSystemSemaphore:
        semaphore = FileSystemSemaphore.acquire(local + MIRROR_SEMAPHORE_EXTENSION)
        if semaphore.leader:
            cls._checkout(remote, local)
        semaphore.synchronize(local + MIRROR_MONITOR_EXTENSION)
        # semaphore is cached to prevent destruction until exit
        return semaphore

    @classmethod
    def _checkout(cls, remote: Remote, local: AbsDir) -> None:
        try:
            cls._clone(remote, local)
        except git.GitCommandError:
            try:
                try:
                    cls._sync(local)
                except git.InvalidGitRepositoryError:
                    shutil.rmtree(local, ignore_errors=True)
                    cls._clone(remote, local)
            except Exception:
                raise git.GitError(f"Unable to checkout {remote}") from None

    @classmethod
    def _clone(cls, remote: Remote, local: AbsDir) -> None:
        with describe(f"Cloning {remote} into {local}", error_level="DEBUG"):
            GitRepo.clone_from(os.fspath(remote), os.fspath(local))

    @classmethod
    def _sync(cls, local: AbsDir) -> None:
        with describe(f"Pulling {cls.repo(local).remote().url} into {local}", error_level="DEBUG"):
            repo = cls.repo(local)
            [fetch_info] = repo.remote().fetch()
            repo.head.reset(fetch_info.commit, working_tree=True, index=True)

    @classmethod
    def fresh_diff(cls, local: AbsDir, file: RelFile) -> str:
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
    def add(cls, local: AbsDir, file: RelFile) -> None:
        # repo.index.add is not syncing
        cls.run_command(local, "add", os.fspath(file))

    @classmethod
    def apply_patch(cls, local: AbsDir, patch: str) -> None:
        cmd: AutoInterrupt = cls.run_command(
            local, "apply", "--allow-empty", "-3", "-", istream=PIPE, as_process=True
        )
        assert cmd.proc is not None
        assert cmd.proc.stdin is not None
        cmd.proc.stdin.write(patch.encode("utf-8"))
        cmd.proc.stdin.close()
        _ret_code = cmd.proc.wait()

    @classmethod
    def commit(cls, local: AbsDir) -> str:
        return cls.repo(local).head.commit.hexsha
