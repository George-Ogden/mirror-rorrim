from __future__ import annotations

from dataclasses import dataclass
import functools
import hashlib
import os.path
from pathlib import Path
import re
from typing import Self, overload


@dataclass(frozen=True, slots=True)
class TypedPath:
    path: Path

    def __init__(self, path: Path | str | Self) -> None:
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
    def canonical(self) -> str:
        # pathlib.Path.resolve uses the filesystem, which could have unwanted links.
        return os.path.normpath(self)

    def __fspath__(self) -> str:
        return self.path.__fspath__()

    def __str__(self) -> str:
        return repr(str(self.path))

    def __lt__(self, other: Self) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return os.fspath(self) < os.fspath(other)


@dataclass(frozen=True, slots=True, init=False)
class RelFile(TypedPath):
    def __add__(self, extension: Ext) -> RelFile:
        return RelFile(f"{self.path}{extension.extension}")


@dataclass(frozen=True, slots=True, init=False)
class AbsFile(TypedPath):
    def __add__(self, extension: Ext) -> AbsFile:
        return AbsFile(f"{self.path}{extension.extension}")


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

    def __add__(self, extension: Ext) -> RelFile:
        return RelFile(f"{self.path}{extension.extension}")


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

    def __add__(self, extension: Ext) -> AbsFile:
        return AbsFile(f"{self.path}{extension.extension}")

    @classmethod
    def cwd(cls) -> Self:
        return cls(Path.cwd())


@dataclass(frozen=True, slots=True)
class GitDir(AbsDir):
    def __init__(self, dir: AbsDir | Path | str, *, check: bool = True) -> None:
        AbsDir.__init__(self, dir)
        if check:
            from .githelper import GitHelper

            GitHelper.repo(self)


@dataclass(frozen=True, slots=True)
class Ext:
    extension: str


@dataclass(frozen=True)
class Remote:
    repo: str

    def __fspath__(self) -> str:
        return self.repo

    def __str__(self) -> str:
        return repr(self.repo)

    @property
    def canonical(self) -> str:
        if os.path.exists(self):
            # Distinguish common relative paths (eg ".").
            return os.path.realpath(self)
        return self._without_trailing_slashes()

    def _without_trailing_slashes(self) -> str:
        strip_trailing_slash_pattern = r"^(.*?)\/*$"
        match = re.match(strip_trailing_slash_pattern, self.repo)
        assert match is not None
        return match.group(1)

    @functools.cached_property
    def hash(self) -> str:
        return hashlib.blake2b(
            bytes(self.canonical, encoding="utf-8", errors="ignore"), usedforsecurity=False
        ).hexdigest()
