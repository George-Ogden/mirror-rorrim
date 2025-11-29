import contextlib
from dataclasses import dataclass
import os
from subprocess import PIPE
from typing import Self

import git
from git.cmd import _AutoInterrupt as AutoInterrupt

from .typed_path import AbsDir, RelFile


@dataclass
class Diff:
    file: RelFile
    patch: str

    @classmethod
    def new_file(cls, repo: AbsDir, file: RelFile) -> Self:
        # gitpython-developers/GitPython#2085
        cmd: AutoInterrupt = git.Repo(os.fspath(repo)).git.diff(
            "--no-index", "--", os.devnull, os.fspath(file), as_process=True
        )
        assert cmd.proc is not None
        assert cmd.proc.stdout is not None
        _ret_code = cmd.proc.wait()
        stdout = git.safe_decode(cmd.proc.stdout.read())
        assert stdout is not None
        _header, patch = stdout.split("\n", maxsplit=1)
        return cls(
            file=file,
            patch=patch,
        )

    def apply(self, local: AbsDir) -> None:
        # gitpython-developers/GitPython#2085
        repo = git.Repo(os.fspath(local))
        with contextlib.suppress(git.GitCommandError):
            # repo.index.add is not syncing
            repo.git.add(os.fspath(self.file))
        cmd: AutoInterrupt = repo.git.apply(
            "--allow-empty", "-3", "-", istream=PIPE, as_process=True
        )
        assert cmd.proc is not None
        assert cmd.proc.stdin is not None
        cmd.proc.stdin.write(self.patch.encode("utf-8"))
        cmd.proc.stdin.close()
        _ret_code = cmd.proc.wait()
