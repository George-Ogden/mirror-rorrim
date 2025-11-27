from collections.abc import Callable, Generator
import tempfile
from unittest import mock

from inline_snapshot import snapshot
import pytest

from .githelper import GitHelper
from .repo import MirrorRepo, MissingFileError
from .test_utils import add_commit, quick_mirror_repo
from .typed_path import AbsDir


@pytest.fixture
def mocked_cache_dir(typed_tmp_path: AbsDir) -> Generator[AbsDir]:
    with mock.patch("src.repo.MIRROR_CACHE", typed_tmp_path):
        yield typed_tmp_path


def checkout_with_missing_file_test_case() -> tuple[
    Callable[[], MirrorRepo], tuple[type[MissingFileError], str]
]:
    remote = tempfile.mkdtemp()
    add_commit(remote, dict.fromkeys(["file1", "file3"]))
    return lambda: quick_mirror_repo(remote, ["file1", ("file2", "file3")]), (
        MissingFileError,
        snapshot(),
    )


def checkout_not_behind_repository_test_case() -> tuple[Callable[[], MirrorRepo], None]:
    def setup_repo() -> MirrorRepo:
        remote = tempfile.mkdtemp()
        add_commit(remote, dict.fromkeys(["file1"]))
        repo = quick_mirror_repo(remote, ["file1", "file2"])
        GitHelper._clone(repo.source, repo.cache)
        add_commit(remote, dict.fromkeys(["file1", "file2"]))
        return repo

    return setup_repo, None


def checkout_not_a_git_repo_test_case() -> tuple[Callable[[], MirrorRepo], None]:
    def setup_repo() -> MirrorRepo:
        remote = tempfile.mkdtemp()
        add_commit(remote, dict.fromkeys(["file1"]))
        repo = quick_mirror_repo(remote, ["file1"])
        repo.cache.path.mkdir()
        (repo.cache.path / "file").touch()
        return repo

    return setup_repo, None


@pytest.mark.parametrize(
    "setup_repo, error",
    [
        (
            lambda: quick_mirror_repo(
                "https://github.com/George-Ogden/actions/",
                ["version.txt"],
            ),
            None,
        ),
        checkout_with_missing_file_test_case(),
        checkout_not_behind_repository_test_case(),
        checkout_not_a_git_repo_test_case(),
    ],
)
def test_checkout(
    mocked_cache_dir: AbsDir,
    setup_repo: Callable[[], MirrorRepo],
    error: None | tuple[type[Exception], str],
) -> None:
    # Use callable to get access to the mocked cache dir.
    repo = setup_repo()
    if error is None:
        repo.checkout()
    else:
        error_type, error_msg = error
        with pytest.raises(error_type) as e:
            repo.checkout()
        error_msg = str(e.value)
        assert error_msg == error_msg
        assert error_msg.endswith(".")
