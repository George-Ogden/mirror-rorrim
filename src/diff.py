import contextlib
from dataclasses import dataclass
import os
from typing import Self

import git

from .file import MirrorFile
from .githelper import GitHelper
from .typed_path import AbsDir


@dataclass
class Diff:
    file: MirrorFile
    patch: str

    @classmethod
    def new_file(cls, repo: AbsDir, file: MirrorFile) -> Self:
        patch = GitHelper.fresh_diff(repo, file.source)
        _header, *patch_lines = patch.splitlines(keepends=True)
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
        with contextlib.suppress(git.GitCommandError):
            GitHelper.add(local, self.file.target)
        GitHelper.apply_patch(local, self.patch)
