from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import SupportsWrite


class State:
    def dump(self, f: SupportsWrite[str]) -> None:
        f.write(" ")
