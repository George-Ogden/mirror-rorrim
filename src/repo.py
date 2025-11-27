from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self

from .config import MirrorRepoConfig
from .constants import MIRROR_CACHE
from .file import MirrorFile
from .githelper import GitHelper
from .typed_path import AbsDir, RelDir, RelFile, Remote


@dataclass
class MissingFileError(Exception):
    source: Remote
    file: RelFile

    def __str__(self) -> str:
        return f"{self.file} could not be found from {self.source}."


@dataclass(frozen=True)
class MirrorRepo:
    source: Remote
    files: Sequence[MirrorFile]

    @classmethod
    def from_config(cls, config: MirrorRepoConfig) -> Self:
        return cls(config.source, [MirrorFile.from_config(subconfig) for subconfig in config.files])

    @property
    def cache(self) -> AbsDir:
        return MIRROR_CACHE / RelDir(self.source.hash)

    def checkout(self) -> None:
        GitHelper.checkout(self.source, self.cache)
        self.verify_all_files_exist()

    def verify_all_files_exist(self) -> None:
        for file in self.files:
            if not file.exists_in(self.cache):
                raise MissingFileError(self.source, file.source)
