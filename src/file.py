from dataclasses import dataclass
from typing import Self

from .config import MirrorFileConfig
from .typed_path import AbsDir, Commit, RelFile


@dataclass(frozen=True, kw_only=True)
class MirrorFile:
    source: RelFile
    target: RelFile

    @classmethod
    def from_config(cls, config: MirrorFileConfig) -> Self:
        return cls(source=config.source, target=config.target)

    def exists_in(self, folder: AbsDir) -> bool:
        path = folder / self.source
        return path.exists()

    def is_file_in(self, folder: AbsDir) -> bool:
        path = folder / self.source
        return path.is_file()

    def is_folder_in(self, folder: AbsDir) -> bool:
        path = folder / self.source
        return path.is_folder()


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
