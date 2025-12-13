from __future__ import annotations

from dataclasses import dataclass
import functools
from typing import TYPE_CHECKING

from yaml import YAMLError

from .config import MirrorConfig
from .config_parser import Parser
from .constants import MIRROR_FILE
from .lock import FileSystemLock
from .manager import MirrorManager
from .mirror import Mirror
from .state import MirrorState

if TYPE_CHECKING:
    from sys import _ExitCode


@dataclass(frozen=True)
class MirrorChecker(MirrorManager):
    def check(self) -> _ExitCode:
        return self._run(self._check, keep_lock_on_failure=True)

    def _check(self) -> _ExitCode:
        return self.mirror.check()

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
