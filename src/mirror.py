from collections.abc import Sequence
from dataclasses import dataclass

from .repo import MirrorRepo


@dataclass(frozen=True)
class Mirror:
    repos: Sequence[MirrorRepo]
