from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Self, cast

from loguru import logger

from .config import MirrorRepoConfig
from .constants import MIRROR_CACHE
from .diff import Diff
from .file import VersionedMirrorFile
from .githelper import GitHelper
from .logger import describe
from .state import MirrorRepoState
from .typed_path import GitDir, RelDir, RelFile, Remote
from .types import Commit


@dataclass
class MissingFileError(Exception):
    source: Remote
    file: RelFile

    def __str__(self) -> str:
        return f"{self.file} could not be found from {self.source}."


@dataclass
class IsADirectoryError(Exception):
    source: Remote
    file: RelFile

    def __str__(self) -> str:
        return f"{self.file} from {self.source} is a directory."


@dataclass
class IrregularFileError(Exception):
    source: Remote
    file: RelFile

    def __str__(self) -> str:
        return f"{self.file} from {self.source} is not a regular file."


@dataclass(frozen=True)
class MirrorRepo:
    source: Remote
    files: Sequence[VersionedMirrorFile]

    @classmethod
    def from_config(cls, config: MirrorRepoConfig, state: MirrorRepoState | None) -> Self:
        assert state is None or config.source.canonical == state.source.canonical
        versioned_filepaths = set() if state is None else set(state.files)
        return cls(
            config.source,
            [
                VersionedMirrorFile.from_config(
                    subconfig,
                    commit=cast(MirrorRepoState, state).commit
                    if subconfig.source in versioned_filepaths
                    else None,
                )
                for subconfig in config.files
            ],
        )

    @property
    def cache(self) -> GitDir:
        return GitDir(MIRROR_CACHE / RelDir(self.source.hash), check=False)

    def checkout(self) -> None:
        with describe(f"Syncing {self.source}", level="DEBUG"):
            GitHelper.checkout(self.source, self.cache)
        self.verify_all_files_exist()

    def verify_all_files_exist(self) -> None:
        for file in self.files:
            if not file.exists_in(self.cache):
                raise MissingFileError(self.source, file.source)
            if file.is_folder_in(self.cache):
                raise IsADirectoryError(self.source, file.source)
            if not file.is_file_in(self.cache):
                raise IrregularFileError(self.source, file.source)

    def all_up_to_date(self) -> bool:
        return all([self.up_to_date(file) for file in self.files])

    def up_to_date(self, file: VersionedMirrorFile) -> bool:
        up_to_date = self.commit == file.commit
        if not up_to_date:
            if file.commit is None:
                logger.info(f"{file.source!s} has not been mirrored from {self.source}.")
            else:
                logger.info(
                    f"{file.source!s} has commit {file.commit}, but {self.source} has commit {self.commit}."
                )
        return up_to_date

    def diffs(self) -> Iterable[Diff]:
        for file in self.files:
            yield Diff.new_file(self.cache, file.file)

    def update(self, target: GitDir) -> None:
        for diff in self.diffs():
            diff.apply(target)

    @property
    def state(self) -> MirrorRepoState:
        return MirrorRepoState(
            source=self.source,
            commit=self.commit,
            files=sorted({file.source for file in self.files}),
        )

    @property
    def commit(self) -> Commit:
        return Commit(GitHelper.commit(self.cache))
