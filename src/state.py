from __future__ import annotations

from collections.abc import Sequence
import dataclasses
from dataclasses import dataclass
import os
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

import yaml

from .typed_path import RelFile, Remote

if TYPE_CHECKING:
    from _typeshed import SupportsWrite


class WriteableState(Protocol):
    def dump(self, f: SupportsWrite[str]) -> None: ...


class AutoState(yaml.YAMLObject):
    yaml_tag = None

    def dump(self, f: SupportsWrite[str]) -> None:
        f.write(yaml.safe_dump(self.representation, default_flow_style=False))

    @classmethod
    def represent(cls, obj: Any) -> Any:
        match obj:
            case _ if dataclasses.is_dataclass(obj):
                return {
                    attr.name: cls.represent(getattr(obj, attr.name))
                    for attr in dataclasses.fields(obj)
                }
            case list() | set() | tuple():
                return [cls.represent(sub_obj) for sub_obj in obj]
            case os.PathLike():
                return os.fspath(obj)
            case str():
                return obj
        raise TypeError()

    @property
    def representation(self) -> Any:
        return self.represent(self)


@dataclass(frozen=True, slots=True)
class MirrorRepoState(AutoState):
    source: Remote
    commit: str
    files: Sequence[RelFile]


@dataclass(frozen=True, slots=True)
class MirrorState(AutoState):
    comment: ClassVar[str] = (
        "DANGER: EDIT AT YOUR OWN RISK. Track this file in version control so that others can use it."
    )
    repos: Sequence[MirrorRepoState]
