from dataclasses import dataclass

from .constants import MIRROR_FILE
from .file import MirrorFile
from .repo import MirrorRepo
from .typed_path import AbsDir, RelFile, Remote


@dataclass(frozen=True, slots=True)
class Installer:
    target: AbsDir
    source_remote: Remote | None
    source_path: RelFile

    @property
    def source_repo(self) -> MirrorRepo | None:
        if self.source_remote is None:
            return None
        mirror_repo = MirrorRepo(
            source=self.source_remote,
            files=[MirrorFile(source=self.source_path, target=MIRROR_FILE)],
        )
        # missing checkout
        return mirror_repo
