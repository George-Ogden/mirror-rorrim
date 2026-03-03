from dataclasses import dataclass

from loguru import logger

from .manager import ExistingMirrorManager


@dataclass(frozen=True)
class MirrorSyncer(ExistingMirrorManager):
    def sync(self) -> None:
        self._run(self._sync, keep_lock_on_failure=True)
        logger.success("All synced!")

    def _sync(self) -> None:
        self.checkout_all()
        self.update_all()
