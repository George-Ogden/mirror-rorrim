import contextlib
from dataclasses import dataclass
import functools
import shutil
from typing import cast

from loguru import logger

from .config import MirrorConfig
from .config_parser import Parser
from .constants import MIRROR_FILE
from .file import MirrorFile, VersionedMirrorFile
from .lock import FileSystemLock
from .logger import describe
from .manager import MirrorManager
from .mirror import Mirror
from .repo import MirrorRepo
from .typed_path import AbsFile, RelFile, Remote
from .utils import strict_cast

type InstallSource = AbsFile | RelFile | tuple[Remote, RelFile]


@dataclass(frozen=True)
class MirrorInstaller(MirrorManager):
    source: InstallSource

    def install(self) -> None:
        self._run(self._install, keep_lock_on_failure=False)

    def _install(self) -> None:
        self.checkout_all()
        self.update_all()

    @functools.cached_property
    def mirror(self) -> Mirror:
        return Mirror.from_config(self.load_config(), state=None)

    @functools.cached_property
    def lock(self) -> FileSystemLock:
        return self._new_lock()

    def load_config(self) -> MirrorConfig:
        if self.source_repo is None:
            config = Parser.parse_file(self.source_path)
        else:
            with describe("Fetching config"):
                [file] = self.source_repo.files
            config = Parser.parse_file(self.source_repo.cache / file.source)
        return config

    @property
    def source_repo(self) -> MirrorRepo | None:
        if self.source_remote is None:
            return None
        mirror_repo = MirrorRepo(
            source=self.source_remote,
            files=[
                VersionedMirrorFile(
                    MirrorFile(source=cast(RelFile, self.source_path), target=MIRROR_FILE),
                    commit=None,
                )
            ],
        )
        mirror_repo.checkout()
        return mirror_repo

    @property
    def source_remote(self) -> Remote | None:
        match self.source:
            case [remote, _]:
                return cast(Remote, remote)
        return None

    @property
    def source_path(self) -> RelFile | AbsFile:
        match self.source:
            case [_, path]:
                return cast(RelFile, path)
        return cast(RelFile | AbsFile, self.source)

    @property
    def mirror_source(self) -> RelFile | AbsFile:
        return (
            self.source_path
            if self.source_repo is None
            else self.source_repo.cache / strict_cast(RelFile, self.source_path)
        )

    def copy_mirror_file(self) -> None:
        mirror_target = self.target / MIRROR_FILE
        mirror_file_existed = (mirror_target).exists()
        with contextlib.suppress(shutil.SameFileError):
            shutil.copy2(self.mirror_source, self.target / MIRROR_FILE)
            if mirror_file_existed:
                logger.warning(f"{MIRROR_FILE} has been overwritten during installation.")

    def _update_all(self) -> None:
        self.copy_mirror_file()
        if self.source_repo is not None:
            self.source_repo.update(self.target)
        super()._update_all()
