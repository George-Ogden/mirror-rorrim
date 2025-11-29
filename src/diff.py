import contextlib
from dataclasses import dataclass
import os
from subprocess import PIPE
from typing import Self

import git
from git.cmd import _AutoInterrupt as AutoInterrupt

from .file import MirrorFile
from .typed_path import AbsDir


@dataclass
class Diff:
    file: MirrorFile
    patch: str

    @classmethod
    def new_file(cls, repo: AbsDir, file: MirrorFile) -> Self:
        # gitpython-developers/GitPython#2085
        cmd: AutoInterrupt = git.Repo(os.fspath(repo)).git.diff(
            "--no-index", "--", os.devnull, os.fspath(file.source), as_process=True
        )
        assert cmd.proc is not None
        assert cmd.proc.stdout is not None
        _ret_code = cmd.proc.wait()
        stdout: str = git.safe_decode(cmd.proc.stdout.read())
        _header, *patch_lines = stdout.splitlines(keepends=True)
        cls.update_patch_lines(patch_lines, file)
        return cls(
            file=file,
            patch="".join(patch_lines),
        )

    @classmethod
    def update_patch_lines(cls, patch_lines: list[str], file: MirrorFile) -> None:
        for i, line in enumerate(patch_lines):
            if line.startswith("+++"):
                line = cls._addition(file)
            elif line.startswith("@@"):
                # Delete header.
                patch_lines.pop(0)
                return
            else:
                continue
            patch_lines[i] = line
        # Patch must be empty, so add extra lines.
        cls._update_empty_patch_lines(patch_lines, file)

    @classmethod
    def _update_empty_patch_lines(cls, patch_lines: list[str], file: MirrorFile) -> None:
        patch_lines.insert(0, cls._empty_header(file))
        patch_lines.extend((cls._addition(file), cls._empty_deletion()))

    @classmethod
    def _empty_header(cls, file: MirrorFile) -> str:
        return f"diff --git a/{os.fspath(file.target)} b/{os.fspath(file.target)}\n"

    @classmethod
    def _addition(cls, file: MirrorFile) -> str:
        return f"+++ b/{os.fspath(file.target)}\n"

    @classmethod
    def _empty_deletion(cls) -> str:
        return f"--- {os.devnull}\n"

    def apply(self, local: AbsDir) -> None:
        # gitpython-developers/GitPython#2085
        repo = git.Repo(os.fspath(local))
        with contextlib.suppress(git.GitCommandError):
            # repo.index.add is not syncing
            repo.git.add(os.fspath(self.file.target))
        cmd: AutoInterrupt = repo.git.apply(
            "--allow-empty", "-3", "-", istream=PIPE, as_process=True
        )
        assert cmd.proc is not None
        assert cmd.proc.stdin is not None
        cmd.proc.stdin.write(self.patch.encode("utf-8"))
        cmd.proc.stdin.close()
        _ret_code = cmd.proc.wait()
