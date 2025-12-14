import contextlib
from dataclasses import KW_ONLY, dataclass
import os
from typing import Self

import git
from loguru import logger

from .file import MirrorFile, VersionedMirrorFile
from .githelper import GitHelper
from .logger import describe
from .typed_path import GitDir
from .types import Commit


@dataclass
class Diff:
    file: MirrorFile
    _: KW_ONLY
    patch: str
    blob: bytes | None

    @classmethod
    def from_file(cls, repo: GitDir, file: VersionedMirrorFile) -> Self:
        return cls.from_commit(file.commit, repo, file.file)

    @classmethod
    def from_commit(cls, commit: None | Commit, repo: GitDir, file: MirrorFile) -> Self:
        if commit is None:
            return cls.empty(repo, file)
        return cls._from_commit(commit, repo, file)

    @classmethod
    def _from_commit(cls, commit: Commit, repo: GitDir, file: MirrorFile) -> Self:
        patch = GitHelper.file_diff(repo, commit, file.source)
        blob = GitHelper.file_blob(repo, commit, file.source)
        return cls(file=file, patch=cls.update_patch(patch, file, new=False), blob=blob)

    @classmethod
    def empty(cls, repo: GitDir, file: MirrorFile) -> Self:
        patch = GitHelper.fresh_diff(repo, file.source)
        return cls(file=file, patch=cls.update_patch(patch, file, new=True), blob=None)

    @classmethod
    def update_patch(cls, patch: str, file: MirrorFile, *, new: bool) -> str:
        if not new and not patch:
            return patch
        _header, *patch_lines = patch.splitlines(keepends=True)
        cls.update_patch_lines(patch_lines, file, new=new)
        return "".join(patch_lines)

    @classmethod
    def update_patch_lines(cls, patch_lines: list[str], file: MirrorFile, *, new: bool) -> None:
        for i, line in enumerate(patch_lines):
            if line.startswith("+++"):
                line = cls._addition(file)
            elif line.startswith("---") and not new:
                line = cls._deletion(file)
            elif line.startswith("@@"):
                # Insert header.
                if not new:
                    patch_lines.insert(0, cls._header(file))
                return
            else:
                continue
            patch_lines[i] = line
        # Patch must be empty, so add extra lines.
        cls._update_empty_patch_lines(patch_lines, file)

    @classmethod
    def _update_empty_patch_lines(cls, patch_lines: list[str], file: MirrorFile) -> None:
        patch_lines.insert(0, cls._header(file))
        patch_lines.extend((cls._addition(file), cls._empty_deletion()))

    @classmethod
    def _header(cls, file: MirrorFile) -> str:
        return f"diff --git a/{os.fspath(file.target)} b/{os.fspath(file.target)}\n"

    @classmethod
    def _addition(cls, file: MirrorFile) -> str:
        return f"+++ b/{os.fspath(file.target)}\n"

    @classmethod
    def _deletion(cls, file: MirrorFile) -> str:
        return f"--- a/{os.fspath(file.target)}\n"

    @classmethod
    def _empty_deletion(cls) -> str:
        return f"--- {os.devnull}\n"

    def apply(self, local: GitDir) -> None:
        with contextlib.suppress(git.GitCommandError):
            GitHelper.add(local, self.file.target)
        with describe(f"Applying patch from {self.file.source} to {self.file.target}"):
            logger.trace(f"patch = {self.patch}")
            GitHelper.apply_patch(local, self.patch)
