import pytest

from .constants import MIRROR_FILE
from .repo import MirrorRepo
from .test_utils import quick_installer, quick_mirror_repo
from .typed_path import RelFile


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
