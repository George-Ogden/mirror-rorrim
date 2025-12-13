import os
from unittest import mock

import pytest
from syrupy.assertion import SnapshotAssertion

from .constants import MIRROR_FILE
from .installer import MirrorInstaller
from .repo import MirrorRepo
from .test_utils import quick_mirror_repo, setup_repo, snapshot_of_repo
from .typed_path import AbsDir, GitDir, RelDir, RelFile, Remote


@pytest.fixture
def test_data_path(global_test_data_path: AbsDir) -> AbsDir:
    return global_test_data_path / RelDir("installer_tests")


def quick_installer(
    target: None | str | AbsDir, remote: tuple[str | None | Remote, str | RelFile | None] | None
) -> MirrorInstaller:
    source_remote, source_path = remote or (None, None)
    source_remote = None if source_remote is None else Remote(os.fspath(source_remote))
    source_path = RelFile(source_path or MIRROR_FILE)
    source = source_path if source_remote is None else (source_remote, source_path)
    return MirrorInstaller(
        source=source,
        target=GitDir(target or AbsDir.cwd()),
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
    installer = quick_installer(None, (source_remote, source_path))
    with mock.patch.object(MirrorRepo, "checkout", mock.Mock(return_value=None)):
        assert installer.source_repo == expected_repo


@pytest.mark.parametrize(
    "test_name, source",
    [
        pytest.param("empty_repo_with_config", None, marks=[pytest.mark.slow]),
        pytest.param("repo_with_multiple_configs", (None, "config.yaml"), marks=[pytest.mark.slow]),
        (
            "remote_only",
            ("https://github.com/George-Ogden/mirror-rorrim-test-data", "config-only.yaml"),
        ),
        (
            "remote_config_overwrite",
            ("https://github.com/George-Ogden/mirror-rorrim-test-data", "config-only.yaml"),
        ),
        ("same_directory", None),
    ],
)
def test_installer_install(
    test_name: str,
    source: tuple[None | str, str] | None,
    local_git_repo: GitDir,
    test_data_path: AbsDir,
    snapshot: SnapshotAssertion,
) -> None:
    installer = quick_installer(local_git_repo, source)
    setup_repo(local_git_repo, test_data_path / RelDir(test_name))

    if isinstance(installer.source, RelFile):
        object.__setattr__(installer, "source", local_git_repo / installer.source)
    installer.install()
    assert snapshot_of_repo(local_git_repo, include_lockfile=False) == snapshot
