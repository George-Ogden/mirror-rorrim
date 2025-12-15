import pytest
from syrupy.assertion import SnapshotAssertion

from .syncer import MirrorSyncer
from .test_utils import setup_repo, snapshot_of_repo
from .typed_path import AbsDir, GitDir, RelDir


@pytest.fixture
def test_data_path(global_test_data_path: AbsDir) -> AbsDir:
    return global_test_data_path / RelDir("syncer_tests")


def quick_syncer(target: None | str | AbsDir) -> MirrorSyncer:
    return MirrorSyncer(GitDir(target or AbsDir.cwd()))


@pytest.mark.parametrize(
    "test_name",
    [
        "up_to_date",
        "behind",
        "new_repo",
        pytest.param("multiple_remotes", marks=[pytest.mark.local, pytest.mark.slow]),
        "diverged_up_to_date",
    ],
)
def test_installer_install(
    test_name: str,
    local_git_repo: GitDir,
    test_data_path: AbsDir,
    snapshot: SnapshotAssertion,
) -> None:
    syncer = quick_syncer(local_git_repo)
    setup_repo(local_git_repo, test_data_path / RelDir(test_name))
    syncer.sync()
    assert snapshot_of_repo(local_git_repo, include_lockfile=True) == snapshot
