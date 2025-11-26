from __future__ import annotations

from dataclasses import dataclass
import io
import os.path
from pathlib import Path
from typing import overload


@dataclass(frozen=True, slots=True)
class TypedPath:
    path: Path

    def __init__(self, path: Path | str) -> None:
        if type(self) is TypedPath:
            raise TypeError()
        object.__setattr__(self, "path", Path(path))

    def _join[T: TypedPath](self, other: TypedPath, type_: type[T]) -> T:
        return type_(self.path / other.path)

    def exists(self) -> bool:
        return self.path.exists()

    def is_file(self) -> bool:
        return self.path.is_file()

    def is_folder(self) -> bool:
        return self.path.is_dir()

    @property
    def normpath(self) -> str:
        return os.path.normpath(self)

    def __fspath__(self) -> str:
        return self.path.__fspath__()

    def __str__(self) -> str:
        return repr(str(self.path))


@dataclass(frozen=True, slots=True, init=False)
class RelFile(TypedPath): ...


@dataclass(frozen=True, slots=True, init=False)
class AbsFile(TypedPath): ...


@dataclass(frozen=True, slots=True, init=False)
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


@dataclass(frozen=True, slots=True, init=False)
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


@dataclass(frozen=True, slots=True)
class Remote:
    repo: str


type PyFile = io.TextIOWrapper
