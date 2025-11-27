from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self

from .config import MirrorConfig
from .repo import MirrorRepo


@dataclass(frozen=True)
class Mirror:
    repos: Sequence[MirrorRepo]

    @classmethod
    def from_config(cls, config: MirrorConfig) -> Self:
        return cls([MirrorRepo.from_config(sub_config) for sub_config in config.repos])
