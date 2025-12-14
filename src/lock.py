from __future__ import annotations

import contextlib
from dataclasses import dataclass
import errno
import fcntl
import time
from typing import ClassVar, Self

from .constants import MIRROR_NAME
from .state import ReadableState, WriteableState
from .typed_path import AbsFile
from .types import PyFile


@dataclass(frozen=True)
class FileSystemLock:
    file: PyFile

    def __del__(self) -> None:
        self.release()

    @classmethod
    def create(cls, filepath: AbsFile) -> Self:
        try:
            file = open(filepath, "x")  # noqa: SIM115
            lock = cls.acquire_non_blocking(file)
            if lock is None:
                file.close()
                raise OSError(
                    f"{filepath.path} is in use by another process. Wait for it to finish then trying again. (You may need to delete this file first.)"
                )
        except OSError as e:
            if e.errno == errno.EEXIST:
                raise FileExistsError(
                    f"{filepath.path} - have you already installed {MIRROR_NAME}? If not, delete this file and try again."
                ) from None
            raise e
        return lock

    @classmethod
    def edit(cls, filepath: AbsFile) -> Self:
        try:
            file = open(filepath, "r+")  # noqa: SIM115
            lock = cls.acquire_non_blocking(file)
            if lock is None:
                file.close()
                raise OSError(
                    f"{filepath.path} is in use by another process. Wait for it to finish then trying again."
                )
        except OSError as e:
            if e.errno == errno.ENOENT:
                raise FileNotFoundError(
                    f"{filepath.path} - have you installed {MIRROR_NAME} yet? If not, install it first."
                ) from None
            raise e
        return lock

    @classmethod
    def acquire_non_blocking(cls, file: PyFile) -> Self | None:
        try:
            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            if e.errno == errno.EWOULDBLOCK:
                return None
            raise e
        return cls(file)

    def release(self) -> None:
        self.file.close()

    def unlock(self, state: WriteableState) -> None:
        try:
            self.dump(state)
        finally:
            self.release()

    def dump(self, state: WriteableState) -> None:
        self.file.seek(0)
        state.dump(self.file)
        self.file.truncate()

    def load[T: ReadableState](self, loader: type[T]) -> T:
        self.file.seek(0)
        return loader.load(self.file)


@dataclass(frozen=True)
class FileSystemSemaphore:
    semaphore: PyFile
    leader: bool
    key: str
    TIMEOUT_SECONDS: ClassVar[float] = 1.0

    def __del__(self) -> None:
        self.release()

    @classmethod
    def acquire(cls, filepath: AbsFile) -> Self:
        file = open(filepath, "a+")  # noqa: SIM115
        try:
            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            cls.write_key(file)
        except OSError:
            leader = False
        else:
            leader = True
        fcntl.flock(file, fcntl.LOCK_SH)
        time = cls.read_key(file)
        return cls(file, leader, time)

    @classmethod
    def write_key(cls, file: PyFile) -> None:
        file.seek(0)
        file.write(str(time.time_ns()))
        file.truncate()
        file.flush()

    @classmethod
    def read_key(cls, file: PyFile) -> str:
        file.seek(0)
        return file.read()

    def synchronize(self, monitor: AbsFile) -> None:
        if self.leader:
            self.notify(monitor)
        else:
            self.wait(monitor)

    def notify(self, monitor: AbsFile) -> None:
        with open(monitor, "w") as f:
            f.write(self.key)
            f.flush()

    def wait(self, monitor: AbsFile) -> None:
        start_time = time.time()
        while time.time() < start_time + self.TIMEOUT_SECONDS:
            with contextlib.suppress(OSError), open(monitor) as f:
                if f.read() == self.key:
                    return
            time.sleep(0.01)
        raise TimeoutError("Wait timed out while waiting for another process to complete the task.")

    def release(self) -> None:
        self.semaphore.close()
