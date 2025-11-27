from dataclasses import dataclass

from .typed_path import RelFile


@dataclass(frozen=True)
class MirrorFile:
    source: RelFile
    target: RelFile
