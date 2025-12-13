import abc
from collections.abc import Callable
from dataclasses import dataclass
import functools
import os

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

    @functools.cached_property
    def lock(self) -> FileSystemLock:
        return FileSystemLock.create(self.lock_file)

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
