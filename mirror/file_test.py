from collections.abc import Callable

import pytest

from .file import MirrorFile, VersionedMirrorFile
from .test_utils import add_commit, quick_mirror_file, quick_versioned_mirror_file
from .typed_path import AbsDir, GitDir, RelDir


@pytest.fixture
def test_data_path(global_test_data_path: AbsDir) -> AbsDir:
    return global_test_data_path / RelDir("file_tests")


@pytest.mark.parametrize(
    "file, exists, is_folder",
    [
        # existing file same source and target
        (quick_mirror_file("exists.yes"), True, False),
        # existing file different source and target
        (quick_mirror_file("exists.yes", "doesnotexist.no"), True, False),
        # non existing file different source and target
        (quick_mirror_file("doesnotexist.no", "exists.yes"), False, False),
        # existing folder
        (quick_mirror_file("folder"), True, True),
        # existing nested file
        (quick_mirror_file("folder/nested.it"), True, False),
        # non existing nested file that
        (quick_mirror_file("folder/nested.not"), False, False),
    ],
)
def test_file_exists_in(
    file: MirrorFile, exists: bool, is_folder: bool, test_data_path: AbsDir, local_git_repo: GitDir
) -> None:
    add_commit(local_git_repo, test_data_path)
    assert file.exists_in(local_git_repo) == exists
    assert file.is_file_in(local_git_repo) == (exists and not is_folder)
    assert file.is_folder_in(local_git_repo) == is_folder


def versioned_file_never_existed_test_case(git_dir: GitDir) -> VersionedMirrorFile:
    commit_id = add_commit(git_dir, dict(file1="file"))
    add_commit(git_dir, dict(file2="file"))
    return quick_versioned_mirror_file("file3", commit=commit_id)


def versioned_file_always_existed_test_case(git_dir: GitDir) -> VersionedMirrorFile:
    commit_id = add_commit(git_dir, dict(file1="filev1"))
    add_commit(git_dir, dict(file1="filev2", file2="file"))
    return quick_versioned_mirror_file("file1", "file2", commit=commit_id)


def versioned_file_deleted_test_case(git_dir: GitDir) -> VersionedMirrorFile:
    commit_id = add_commit(git_dir, dict(file1="filev1", file2="file"))
    add_commit(git_dir, dict(file1="filev2"))
    add_commit(git_dir, dict(file1="filev3", file2="file"))
    return quick_versioned_mirror_file("file2", "file1", commit=commit_id)


def versioned_file_created_test_case(git_dir: GitDir) -> VersionedMirrorFile:
    commit_id = add_commit(git_dir, dict(file1="filev1"))
    add_commit(git_dir, dict(file1="filev2", file2="file"))
    return quick_versioned_mirror_file("file2", "file1", commit=commit_id)


def versioned_file_existed_as_dir_test_case(git_dir: GitDir) -> VersionedMirrorFile:
    commit_id = add_commit(git_dir, {"myster/file": "file"})
    add_commit(git_dir, dict(myster="file"))
    return quick_versioned_mirror_file("file", commit=commit_id)


@pytest.mark.parametrize(
    "setup_repo, exists",
    [
        (versioned_file_never_existed_test_case, False),
        (versioned_file_always_existed_test_case, True),
        (versioned_file_deleted_test_case, True),
        (versioned_file_created_test_case, False),
        (versioned_file_existed_as_dir_test_case, False),
    ],
)
def test_versioned_file_existed_in(
    setup_repo: Callable[[GitDir], VersionedMirrorFile], exists: bool, local_git_repo: GitDir
) -> None:
    versioned_file = setup_repo(local_git_repo)
    assert versioned_file.existed_in(local_git_repo) == exists
