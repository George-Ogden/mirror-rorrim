from __future__ import annotations

import abc
from dataclasses import dataclass
from pathlib import Path
from typing import overload


@dataclass(frozen=True, slots=True)
class TypedPath(abc.ABC):
    path: Path

    @abc.abstractmethod
    def __init__(self, path: Path) -> None: ...

    def _join[T: TypedPath](self, other: TypedPath, type_: type[T]) -> T:
        return type_(self.path / other.path)

    def exists(self) -> bool:
        return self.path.exists()

    def is_file(self) -> bool:
        return self.path.is_file()

    def is_folder(self) -> bool:
        return self.path.is_dir()


@dataclass(frozen=True, slots=True, init=True)
class RelFile(TypedPath): ...


@dataclass(frozen=True, slots=True, init=True)
class AbsFile(TypedPath): ...


@dataclass(frozen=True, slots=True, init=True)
class RelDir(TypedPath):
    @overload
    def __truediv__(self, other: RelFile) -> RelFile: ...
    @overload
    def __truediv__(self, other: RelDir) -> RelDir: ...
    def __truediv__(self, other: TypedPath) -> TypedPath:
        match other:
            case RelFile():
                ret_type: type[TypedPath] = RelFile
            case RelDir():
                ret_type = RelDir
            case _:
                raise TypeError()
        return self._join(other, ret_type)


@dataclass(frozen=True, slots=True, init=True)
class AbsDir(TypedPath):
    @overload
    def __truediv__(self, other: RelFile) -> AbsFile: ...
    @overload
    def __truediv__(self, other: RelDir) -> AbsDir: ...
    def __truediv__(self, other: TypedPath) -> TypedPath:
        match other:
            case RelFile():
                ret_type: type[TypedPath] = AbsFile
            case RelDir():
                ret_type = AbsDir
            case _:
                raise TypeError()
        return self._join(other, ret_type)
