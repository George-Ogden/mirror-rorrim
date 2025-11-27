import pytest

from .constants import MIRROR_FILE
from .file import MirrorFile
from .installer import Installer
from .repo import MirrorRepo
from .typed_path import AbsDir, RelFile, Remote


def quick_installer(source_remote: str | None, source_path: str | RelFile) -> Installer:
    return Installer(
        source_remote=None if source_remote is None else Remote(source_remote),
        source_path=RelFile(source_path),
        target=AbsDir.cwd(),
    )


def quick_mirror_file(source: str | RelFile, target: RelFile | str | None = None) -> MirrorFile:
    if target is None:
        target = source
    return MirrorFile(source=RelFile(source), target=RelFile(target))


def quick_mirror_repo(
    source: str, files: list[tuple[str | RelFile, str | RelFile] | str | RelFile]
) -> MirrorRepo:
    return MirrorRepo(
        source=Remote(source),
        files=[
            quick_mirror_file(*file) if isinstance(file, tuple) else quick_mirror_file(file)
            for file in files
        ],
    )


@pytest.mark.parametrize(
    "source_remote, source_path, expected_repo",
    [
        # local remote
        ("../local_folder", MIRROR_FILE, quick_mirror_repo("../local_folder", [MIRROR_FILE])),
        # nonlocal remote different file
        (
            "https://myremote.com",
            "not-mirror-file",
            quick_mirror_repo("https://myremote.com", [("not-mirror-file", MIRROR_FILE)]),
        ),
        # no remote
        (None, MIRROR_FILE, None),
    ],
)
def test_installer_source_repo(
    source_remote: str | None, source_path: str | RelFile, expected_repo: MirrorRepo | None
) -> None:
    installer = quick_installer(source_remote, source_path)
    assert installer.source_repo == expected_repo
