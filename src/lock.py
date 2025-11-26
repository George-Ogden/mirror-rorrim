import contextlib
from dataclasses import dataclass
import fcntl
from typing import Self

from .typed_path import PyFile


@dataclass(frozen=True)
class FileSystemLock:
    file: PyFile

    def __del__(self) -> None:
        self.release()

    @classmethod
    def acquire_non_blocking(cls, file: PyFile) -> Self | None:
        try:
            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return None
        return cls(file)

    def release(self) -> None:
        with contextlib.suppress(OSError, ValueError):  # may already be unlocked
            fcntl.flock(self.file, fcntl.LOCK_UN)
        self.file.close()
