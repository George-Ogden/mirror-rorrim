import pytest

from .file import MirrorFile
from .test_utils import add_commit, quick_mirror_file
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
def test_exists_in(
    file: MirrorFile, exists: bool, is_folder: bool, test_data_path: AbsDir, local_git_repo: GitDir
) -> None:
    add_commit(local_git_repo, test_data_path)
    assert file.exists_in(local_git_repo) == exists
    assert file.is_file_in(local_git_repo) == (exists and not is_folder)
    assert file.is_folder_in(local_git_repo) == is_folder
