from collections.abc import Sequence
from dataclasses import dataclass
import functools
import os
import shutil
from subprocess import PIPE, Popen
import traceback
from typing import Any, Never, cast

import git
from git import GitCommandError, GitError, InvalidGitRepositoryError, Tree
from git import Repo as GitRepo
from git.cmd import _AutoInterrupt as GitCmd
from loguru import logger

from .constants import MIRROR_MONITOR_EXTENSION, MIRROR_SEMAPHORE_EXTENSION
from .lock import FileSystemSemaphore
from .logger import describe
from .typed_path import AbsDir, GitDir, RelFile, Remote
from .types import Commit
from .utils import strict_not_none


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessResult:
    stdout: str
    stderr: str
    returncode: int
    args: Sequence[str]

    def log(self, level: str) -> None:
        logger.log(level, f"Running: {self.args}")
        logger.log(level, f"stdout:\n{self.stdout}")
        logger.log(level, f"stderr:\n{self.stderr}")
        logger.log(level, f"returncode = {self.returncode}")


class GitHelper:
    @classmethod
    @functools.cache
    def repo(cls, local: GitDir) -> GitRepo:
        # Convert to string explicitly to gitpython-developers/GitPython#2085
        return GitRepo(os.fspath(local))

    @classmethod
    def run_command(
        cls,
        local: GitDir,
        command: str,
        *args: Any,
        stdin: str | bytes | None = None,
        as_process: Never = cast(Never, None),
        istream: Never = cast(Never, None),
        **kwargs: Any,
    ) -> ProcessResult:
        if stdin is not None:
            kwargs["istream"] = PIPE
        cmd: GitCmd = getattr(cls.repo(local).git, command)(*args, **kwargs, as_process=True)
        cls.pipe_stdin(cmd, stdin)
        return cls.wait(cmd)

    @classmethod
    def pipe_stdin(cls, cmd: GitCmd, stdin: str | bytes | None) -> None:
        if stdin is not None:
            cls._pipe_stdin(cmd, stdin)

    @classmethod
    def _pipe_stdin(cls, cmd: GitCmd, stdin: str | bytes) -> None:
        assert cmd.proc is not None
        assert cmd.proc.stdin is not None
        if isinstance(stdin, str):
            stdin = stdin.encode("utf-8")
        cmd.proc.stdin.write(stdin)
        cmd.proc.stdin.close()

    @classmethod
    def wait(cls, process: Popen | GitCmd) -> ProcessResult:
        if isinstance(process, GitCmd):
            process = strict_not_none(process.proc)
        process.wait()
        result = ProcessResult(
            stdout=strict_not_none(git.safe_decode(strict_not_none(process.stdout).read())),
            stderr=strict_not_none(git.safe_decode(strict_not_none(process.stderr).read())),
            returncode=process.returncode,
            args=tuple(cast(Sequence[str], process.args)),
        )
        if result.returncode in (0, 1):
            result.log(level="TRACE")
        else:
            result.log(level="DEBUG")
            raise GitCommandError(
                tuple(result.args),
                status=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        return result

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
        return cls.run_command(
            local, "diff", "--no-index", "--full-index", "--", os.devnull, os.fspath(file)
        ).stdout

    @classmethod
    def file_diff(cls, local: GitDir, commit: Commit, file: RelFile) -> str:
        return cls.run_command(
            local, "diff", "--full-index", commit.sha, "--", os.fspath(file)
        ).stdout

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
        cls.run_command(local, "apply", "--allow-empty", "-3", "-", stdin=patch)

    @classmethod
    def hash_object(cls, local: GitDir, blob: bytes) -> None:
        cls.run_command(local, "hash-object", "--stdin", "-w", stdin=blob)

    @classmethod
    def commit(cls, local: GitDir) -> str:
        return cls.repo(local).head.commit.hexsha

    @classmethod
    def tree(cls, local: GitDir, commit: Commit | None = None) -> Tree:
        return cls.repo(local).tree(None if commit is None else commit.sha)
