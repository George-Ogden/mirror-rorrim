import contextlib
import os
import shutil
from unittest import mock

import pytest
from syrupy.assertion import SnapshotAssertion

from .constants import MIRROR_FILE, MIRROR_LOCK
from .repo import MirrorRepo
from .test_utils import add_commit, quick_installer, quick_mirror_repo
from .typed_path import AbsDir, GitDir, RelDir, RelFile


@pytest.fixture
def test_data_path(global_test_data_path: AbsDir) -> AbsDir:
    return global_test_data_path / RelDir("installer_tests")


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
            ("https://github.com/George-Ogden/remote-installer-test-data", "config-only.yaml"),
        ),
        (
            "remote_config_overwrite",
            ("https://github.com/George-Ogden/remote-installer-test-data", "config-only.yaml"),
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
    add_commit(local_git_repo, None)
    with contextlib.suppress(FileNotFoundError):
        add_commit(local_git_repo, test_data_path / RelDir(test_name))
        shutil.copytree(test_data_path / RelDir(test_name), local_git_repo, dirs_exist_ok=True)

    if isinstance(installer.source, RelFile):
        object.__setattr__(installer, "source", local_git_repo / installer.source)
    installer.install()

    repo_contents = {}
    for folder, _, filenames in local_git_repo.path.walk():
        if ".git" in os.fspath(folder):
            continue
        for filename in filenames:
            filepath = RelDir(folder) / RelFile(filename)
            if RelFile(filename) == MIRROR_LOCK:
                assert os.path.getsize(filepath) > 0
                continue
            with open(filepath) as f:
                repo_contents[os.fspath((folder / filename).relative_to(local_git_repo))] = f.read()
    assert repo_contents == snapshot
