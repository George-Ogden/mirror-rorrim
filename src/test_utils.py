from glob import glob
import os
import shutil
from typing import Any

import git
from pytest import ExceptionInfo

from .constants import MIRROR_FILE
from .file import MirrorFile, VersionedMirrorFile
from .githelper import GitHelper
from .installer import Installer
from .mirror import Mirror
from .repo import MirrorRepo
from .typed_path import AbsDir, RelFile, Remote


def quick_installer(
    target: None | str | AbsDir, remote: tuple[str | None | Remote, str | RelFile | None] | None
) -> Installer:
    source_remote, source_path = remote or (None, None)
    source_remote = None if source_remote is None else Remote(os.fspath(source_remote))
    source_path = RelFile(source_path or MIRROR_FILE)
    source = source_path if source_remote is None else (source_remote, source_path)
    return Installer(
        source=source,
        target=AbsDir(target or AbsDir.cwd()),
    )


def quick_mirror_file(source: str | RelFile, target: RelFile | str | None = None) -> MirrorFile:
    if target is None:
        target = source
    return MirrorFile(source=RelFile(source), target=RelFile(target))


def quick_mirror_repo(
    source: str | AbsDir, files: list[tuple[str | RelFile, str | RelFile] | str | RelFile]
) -> MirrorRepo:
    return MirrorRepo(
        source=Remote(os.fspath(source)),
        files=[
            VersionedMirrorFile(
                quick_mirror_file(*file) if isinstance(file, tuple) else quick_mirror_file(file),
                commit=None,
            )
            for file in files
        ],
    )


def quick_mirror(repos: list[MirrorRepo]) -> Mirror:
    return Mirror(repos)


def add_commit(path: AbsDir | str, files: dict[str, Any] | None | AbsDir = None) -> str:
    path = AbsDir(path)
    # gitpython-developers/GitPython#2085
    repo = git.Repo.init(os.fspath(path))

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
    return commit.hexsha


def normalize_message(e: ExceptionInfo, *, test_data_path: AbsDir) -> str:
    error_msg = str(e.value)
    file_normalized_msg = error_msg.replace(str(test_data_path.path), "TEST_DATA")
    return " ".join(line.strip() for line in file_normalized_msg.splitlines() if line.strip())
