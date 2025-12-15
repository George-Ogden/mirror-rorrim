import abc
from collections.abc import Callable
from dataclasses import dataclass
import functools
import os

from yaml import YAMLError

from .config import MirrorConfig
from .config_parser import Parser
from .constants import MIRROR_FILE, MIRROR_LOCK
from .githelper import GitHelper
from .lock import FileSystemLock
from .logger import describe
from .mirror import Mirror
from .state import MirrorState
from .typed_path import AbsFile, GitDir


@dataclass(frozen=True)
class MirrorManager(abc.ABC):
    target: GitDir

    def _run[T](self, main: Callable[[], T], *, keep_lock_on_failure: bool) -> T:
        lock = self.lock
        try:
            result = main()
            lock.unlock(self.state)
            GitHelper.add(self.target, MIRROR_LOCK, MIRROR_FILE)
            return result
        except BaseException as e:
            if not keep_lock_on_failure:
                os.remove(self.target / MIRROR_LOCK)
            raise e

    @property
    @abc.abstractmethod
    def lock(self) -> FileSystemLock: ...

    def _new_lock(self) -> FileSystemLock:
        return FileSystemLock.create(self.lock_file)

    def _existing_lock(self) -> FileSystemLock:
        return FileSystemLock.edit(self.lock_file)

    @property
    def lock_file(self) -> AbsFile:
        return self.target / MIRROR_LOCK

    @describe("Syncing all repos", level="INFO")
    def checkout_all(self) -> None:
        self._checkout_all()

    def _checkout_all(self) -> None:
        self.mirror.checkout_all()

    @property
    @abc.abstractmethod
    def mirror(self) -> Mirror: ...

    @describe("Updating all files", level="INFO")
    def update_all(self) -> None:
        self._update_all()

    def _update_all(self) -> None:
        self.mirror.update_all(self.target)

    @property
    def state(self) -> MirrorState:
        return self.mirror.state


@dataclass(frozen=True)
class ExistingMirrorManager(MirrorManager):
    @functools.cached_property
    def mirror(self) -> Mirror:
        return Mirror.from_config(self.load_config(), state=self.load_state())

    @functools.cached_property
    def lock(self) -> FileSystemLock:
        return self._existing_lock()

    def load_config(self) -> MirrorConfig:
        return Parser.parse_file(self.target / MIRROR_FILE)

    def load_state(self) -> MirrorState:
        try:
            return self.lock.load(MirrorState)
        except YAMLError as e:
            raise YAMLError(
                f"Error while loading {self.lock_file}: {str(e)[0].lower()}{str(e)[1:]}"
            ) from e
        except BaseException as e:
            raise RuntimeError(
                f"Error while loading {self.lock_file}. ({type(e).__name__}: {e})"
            ) from e
