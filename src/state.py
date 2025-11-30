from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .typed_path import RelFile, Remote

if TYPE_CHECKING:
    from _typeshed import SupportsWrite


class State:
    def dump(self, f: SupportsWrite[str]) -> None:
        f.write(" ")


@dataclass(frozen=True, slots=True)
class MirrorRepoState:
    source: Remote
    commit: str
    files: Sequence[RelFile]
