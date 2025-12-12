from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Self

from .config import MirrorConfig
from .logger import describe
from .repo import MirrorRepo
from .state import MirrorState
from .typed_path import GitDir


@dataclass(frozen=True)
class Mirror:
    repos: Sequence[MirrorRepo]

    @classmethod
    def from_config(cls, config: MirrorConfig) -> Self:
        return cls([MirrorRepo.from_config(sub_config) for sub_config in config.repos])

    def __iter__(self) -> Iterator[MirrorRepo]:
        return iter(self.repos)

    @describe("Checking out all repos", level="INFO")
    def checkout_all(self) -> None:
        for repo in self:
            repo.checkout()

    def update_all(self, target: GitDir) -> None:
        for repo in self:
            repo.update(target)

    @property
    def state(self) -> MirrorState:
        return MirrorState([repo.state for repo in self.repos])
