from __future__ import annotations

from dataclasses import dataclass

from .manager import ExistingMirrorManager
from .types import ExitCode


@dataclass(frozen=True)
class MirrorChecker(ExistingMirrorManager):
    def check(self) -> ExitCode:
        return self._run(self._check, keep_lock_on_failure=True)

    def _check(self) -> ExitCode:
        return self.mirror.check()
