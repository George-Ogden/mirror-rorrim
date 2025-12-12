from dataclasses import dataclass
from typing import Self

from git import Blob, Submodule, Tree

from .config import MirrorFileConfig
from .githelper import GitHelper
from .typed_path import AbsDir, Commit, RelFile


@dataclass(frozen=True, kw_only=True)
class MirrorFile:
    source: RelFile
    target: RelFile

    @classmethod
    def from_config(cls, config: MirrorFileConfig) -> Self:
        return cls(source=config.source, target=config.target)

    def _git_object(self, folder: AbsDir | Tree) -> Blob | Tree | Submodule | None:
        try:
            tree = GitHelper.tree(folder) if isinstance(folder, AbsDir) else folder
            return tree / str(self.source.path)
        except KeyError:
            return None

    def exists_in(self, folder: AbsDir | Tree) -> bool:
        return self._git_object(folder) is not None

    def is_file_in(self, folder: AbsDir | Tree) -> bool:
        return isinstance(self._git_object(folder), Blob)

    def is_folder_in(self, folder: AbsDir | Tree) -> bool:
        return isinstance(self._git_object(folder), Tree)


@dataclass(frozen=True)
class VersionedMirrorFile:
    file: MirrorFile
    commit: Commit | None

    @classmethod
    def from_config(cls, config: MirrorFileConfig) -> Self:
        return cls(file=MirrorFile.from_config(config), commit=None)

    @property
    def source(self) -> RelFile:
        return self.file.source

    @property
    def target(self) -> RelFile:
        return self.file.target

    def exists_in(self, folder: AbsDir) -> bool:
        return self.file.exists_in(folder)

    def is_file_in(self, folder: AbsDir) -> bool:
        return self.file.is_file_in(folder)

    def is_folder_in(self, folder: AbsDir) -> bool:
        return self.file.is_folder_in(folder)
