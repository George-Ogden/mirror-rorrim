from __future__ import annotations

from dataclasses import dataclass

from .manager import ExistingMirrorManager
from .types import ExitCode


@dataclass(frozen=True)
class MirrorChecker(ExistingMirrorManager):
    def check(self) -> ExitCode:
        lock = self.lock
        try:
            return self._check()
        finally:
            lock.release()

    def _check(self) -> ExitCode:
        return self.mirror.check()
