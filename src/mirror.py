from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from loguru import logger

from .config import MirrorConfig
from .logger import describe
from .repo import MirrorRepo
from .state import MirrorState
from .typed_path import GitDir

if TYPE_CHECKING:
    from sys import _ExitCode


@dataclass(frozen=True)
class Mirror:
    repos: Sequence[MirrorRepo]

    @classmethod
    def from_config(cls, config: MirrorConfig, state: MirrorState | None) -> Self:
        index = defaultdict(lambda: None) if state is None else state.index
        return cls(
            [
                MirrorRepo.from_config(sub_config, index[sub_config.source.canonical])
                for sub_config in config.repos
            ]
        )

    def __iter__(self) -> Iterator[MirrorRepo]:
        return iter(self.repos)

    def check(self) -> _ExitCode:
        self.checkout_all()
        up_to_date = self.all_up_to_date()
        if up_to_date:
            logger.info("All up to date!")
        return int(not up_to_date)

    def all_up_to_date(self) -> bool:
        return all([repo.all_up_to_date() for repo in self.repos])

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
