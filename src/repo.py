from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self

from .config import MirrorRepoConfig
from .file import MirrorFile
from .typed_path import Remote


@dataclass(frozen=True)
class MirrorRepo:
    source: Remote
    files: Sequence[MirrorFile]

    @classmethod
    def from_config(cls, config: MirrorRepoConfig) -> Self:
        return cls(config.source, [MirrorFile.from_config(subconfig) for subconfig in config.files])
