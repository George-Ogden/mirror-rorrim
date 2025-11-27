from .file import MirrorFile
from .installer import Installer
from .mirror import Mirror
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


def quick_mirror(repos: list[MirrorRepo]) -> Mirror:
    return Mirror(repos)
