from dataclasses import dataclass

from .typed_path import RelFile, Remote


@dataclass(frozen=True, kw_only=True, slots=True)
class MirrorFileConfig:
    source: RelFile
    target: RelFile


@dataclass(frozen=True, kw_only=True, slots=True)
class MirrorRepoConfig:
    source: Remote
    files: list[MirrorFileConfig]
