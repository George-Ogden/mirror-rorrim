from dataclasses import dataclass
from typing import Self

from .config import MirrorFileConfig
from .typed_path import RelFile


@dataclass(frozen=True)
class MirrorFile:
    source: RelFile
    target: RelFile

    @classmethod
    def from_config(cls, config: MirrorFileConfig) -> Self:
        return cls(source=config.source, target=config.target)
