from dataclasses import dataclass
import functools
import os
from typing import cast

from .config import MirrorConfig
from .config_parser import Parser
from .constants import MIRROR_FILE, MIRROR_LOCK
from .file import MirrorFile
from .githelper import GitHelper
from .lock import FileSystemLock, WriteableState
from .logger import describe
from .mirror import Mirror
from .repo import MirrorRepo
from .typed_path import AbsDir, AbsFile, RelFile, Remote

type InstallSource = AbsFile | RelFile | tuple[Remote, RelFile]


@dataclass(frozen=True)
class Installer:
    target: AbsDir
    source: InstallSource

    def install(self) -> None:
        lock = self.lock()
        try:
            state = self._install()
            lock.unlock(state)
            GitHelper.add(self.target, MIRROR_LOCK)
        except BaseException as e:
            os.remove(self.target / MIRROR_LOCK)
            raise e from e

    def lock(self) -> FileSystemLock:
        return FileSystemLock.create(self.lock_file)

    @property
    def lock_file(self) -> AbsFile:
        return self.target / MIRROR_LOCK

    def _install(self) -> WriteableState:
        self.checkout_all()
        self.update_all()
        return self.state

    @describe("Syncing all repos", level="INFO")
    def checkout_all(self) -> None:
        self.mirror.checkout_all()

    @functools.cached_property
    def mirror(self) -> Mirror:
        return Mirror.from_config(self.load_config())

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
            files=[MirrorFile(source=cast(RelFile, self.source_path), target=MIRROR_FILE)],
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

    @describe("Updating all files", level="INFO")
    def update_all(self) -> None:
        if self.source_repo is not None:
            self.source_repo.update(self.target)
        self.mirror.update_all(self.target)

    @property
    def state(self) -> WriteableState:
        return self.mirror.state
