from __future__ import annotations

import contextlib
from dataclasses import dataclass
import fcntl
from typing import TYPE_CHECKING, Protocol, Self

from .typed_path import AbsFile, PyFile

if TYPE_CHECKING:
    from _typeshed import SupportsWrite


class WriteableState(Protocol):
    def dump(self, f: SupportsWrite[str]) -> None: ...


@dataclass(frozen=True)
class FileSystemLock:
    file: PyFile

    def __del__(self) -> None:
        self.release()

    @classmethod
    def create(cls, filepath: AbsFile) -> Self:
        file = open(filepath, "x")  # noqa: SIM115
        lock = cls.acquire_non_blocking(file)
        if lock is None:
            file.close()
            raise FileExistsError(filepath.path)
        return lock

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

    def unlock(self, state: WriteableState) -> None:
        try:
            state.dump(self.file)
        finally:
            self.release()
