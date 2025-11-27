from collections.abc import Sequence
from dataclasses import dataclass

from .file import MirrorFile
from .typed_path import Remote


@dataclass(frozen=True)
class MirrorRepo:
    source: Remote
    files: Sequence[MirrorFile]
