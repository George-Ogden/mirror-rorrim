from collections.abc import Sequence
import contextlib
from glob import glob
import os
import shutil
from typing import Any, cast, overload

import git
from pytest import ExceptionInfo

from .constants import MIRROR_LOCK
from .file import MirrorFile, VersionedMirrorFile
from .githelper import GitHelper
from .mirror import Mirror
from .repo import MirrorRepo
from .state import MirrorRepoState, MirrorState
from .typed_path import AbsDir, GitDir, RelDir, RelFile, Remote
from .types import Commit


def quick_mirror_file(source: str | RelFile, target: RelFile | str | None = None) -> MirrorFile:
    if target is None:
        target = source
    return MirrorFile(source=RelFile(source), target=RelFile(target))


@overload
def quick_versioned_mirror_file(
    source: str | RelFile, target: RelFile | str | None = None, commit: Commit | str | None = None
) -> VersionedMirrorFile: ...
@overload
def quick_versioned_mirror_file(source: str | RelFile, commit: Commit) -> VersionedMirrorFile: ...


def quick_versioned_mirror_file(  # type: ignore [misc]
    source: str | RelFile,
    target: RelFile | str | None | Commit = None,
    commit: Commit | str | None = None,
) -> VersionedMirrorFile:
    if isinstance(target, Commit):
        commit = target
        target = None
    if target is None:
        target = source
    return VersionedMirrorFile(
        MirrorFile(source=RelFile(source), target=RelFile(target)),
        commit=None if commit is None else commit if isinstance(commit, Commit) else Commit(commit),
    )


def quick_mirror_repo(
    source: str | AbsDir,
    files: list[
        tuple[str | RelFile, str | RelFile | Commit]
        | tuple[str | RelFile, str | RelFile, str | Commit]
        | str
        | RelFile
    ],
) -> MirrorRepo:
    return MirrorRepo(
        source=Remote(os.fspath(source)),
        files=[
            quick_versioned_mirror_file(*file)
            if isinstance(file, tuple)
            else quick_versioned_mirror_file(file)
            for file in files
        ],
    )


def quick_mirror(repos: list[MirrorRepo]) -> Mirror:
    return Mirror(repos)


def quick_mirror_repo_state(source: str, commit: str, files: list[str]) -> MirrorRepoState:
    return MirrorRepoState(Remote(source), Commit(commit), [RelFile(file) for file in files])


def quick_mirror_state(mirror_repos: list[MirrorRepoState]) -> MirrorState:
    return MirrorState(mirror_repos)


def add_commit(path: AbsDir | str, files: dict[str, Any] | None | AbsDir = None) -> Commit:
    # gitpython-developers/GitPython#2085
    repo = git.Repo.init(os.fspath(path))
    path = GitDir(path)

    if files is not None:
        for file in glob(str(path.path / "*")):
            if os.path.isfile(file):
                os.remove(file)
            else:
                shutil.rmtree(file)

    if isinstance(files, AbsDir):
        shutil.copytree(files, path, dirs_exist_ok=True)

    if isinstance(files, dict):
        for filename, contents in files.items():
            relfile = RelFile(filename)
            filepath = path / relfile
            filepath.path.parent.mkdir(exist_ok=True, parents=True)
            with open(filepath, "w") as f:
                f.write(str(contents))
            GitHelper.add(path, relfile)
    else:
        GitHelper.add(path, RelFile("."))
    try:
        num_commits = len(list(repo.iter_commits()))
    except ValueError:
        num_commits = 0
    commit = repo.index.commit(f"Commit {num_commits + 1}")
    return Commit(commit.hexsha)


def normalize_message(
    e: ExceptionInfo | str,
    *,
    test_data_path: AbsDir | None = None,
    git_dir: Sequence[AbsDir] | AbsDir | None = None,
) -> str:
    error_msg = e if isinstance(e, str) else str(e.value)
    error_msg = error_msg.strip()
    if test_data_path is not None:
        error_msg = error_msg.replace(os.fspath(test_data_path), "TEST_DATA")
    if git_dir is not None:
        git_dirs = [git_dir] if isinstance(git_dir, AbsDir) else git_dir
        for git_dir in git_dirs:
            error_msg = error_msg.replace(os.fspath(git_dir), "GIT_DIR")
            with contextlib.suppress(ValueError):
                for commit in GitHelper.repo(git_dir).iter_commits():
                    error_msg = error_msg.replace(commit.hexsha, cast(str, commit.message))
    return (" " * 4).join(line.strip() for line in error_msg.splitlines() if line.strip())


def setup_repo(git_dir: GitDir, data_path: AbsDir) -> None:
    add_commit(git_dir, None)
    with contextlib.suppress(FileNotFoundError):
        add_commit(git_dir, data_path)
        shutil.copytree(data_path, git_dir, dirs_exist_ok=True)


def snapshot_of_repo(git_dir: GitDir, *, include_lockfile: bool) -> dict[str, str]:
    repo_contents = {}
    for folder, _, filenames in git_dir.path.walk():
        if ".git" in os.fspath(folder):
            continue
        for filename in filenames:
            filepath = RelDir(folder) / RelFile(filename)
            if not include_lockfile and RelFile(filename) == MIRROR_LOCK:
                assert os.path.getsize(filepath) > 0
                continue
            with open(filepath) as f:
                repo_contents[os.fspath((folder / filename).relative_to(git_dir))] = f.read()
    return repo_contents
