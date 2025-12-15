import os
import shutil
import stat
import tempfile
import textwrap

import pytest
from syrupy.assertion import SnapshotAssertion

from .diff import Diff
from .file import MirrorFile
from .test_utils import add_commit, quick_mirror_file
from .typed_path import AbsDir, Ext, GitDir, RelDir, RelFile


@pytest.fixture
def test_data_path(global_test_data_path: AbsDir) -> AbsDir:
    return global_test_data_path / RelDir("diff_tests")


@pytest.fixture
def test_name(file: MirrorFile) -> str:
    return os.fspath(file.target)


@pytest.mark.parametrize(
    "file",
    [
        quick_mirror_file("empty"),
        quick_mirror_file("new"),
        quick_mirror_file("conflict"),
        quick_mirror_file("new", "rename"),
        quick_mirror_file("empty", "new-empty"),
        quick_mirror_file("new", "nested/folder/new"),
    ],
)
def test_diff_apply_new_file(
    file: MirrorFile, test_data_path: AbsDir, snapshot: SnapshotAssertion, local_git_repo: GitDir
) -> None:
    remote = AbsDir(tempfile.mkdtemp())
    add_commit(remote, test_data_path / RelDir("remote"))
    diff = Diff.empty(GitDir(remote), file)
    tmp_filepath = local_git_repo / file.target
    tmp_filepath.path.parent.mkdir(parents=True, exist_ok=True)
    current_path = test_data_path / RelDir("local") / file.target
    if current_path.exists():
        shutil.copy2(current_path, tmp_filepath)
    diff.apply(local_git_repo)
    with open(tmp_filepath) as f:
        assert f.read() == snapshot


@pytest.mark.typed
def test_diff_from_no_commit(local_git_repo: GitDir) -> None:
    add_commit(local_git_repo, dict(file1="file1"))
    file = quick_mirror_file("file1", "file2")
    diff = Diff.from_commit(None, local_git_repo, file)
    assert diff == Diff(
        file,
        patch=textwrap.dedent(
            r"""
            new file mode 100644
            index 0000000000000000000000000000000000000000..08219db9b0969fa29cf16fd04df4a63964da0b69
            --- /dev/null
            +++ b/file2
            @@ -0,0 +1 @@
            +file1
            \ No newline at end of file
            """
        ).lstrip(),
        blob=None,
    )


@pytest.mark.typed
def test_diff_from_commit_non_empty(local_git_repo: GitDir) -> None:
    initial_commit = add_commit(local_git_repo, dict(file1="filev1"))
    add_commit(local_git_repo, dict(file1="filev2"))
    file = quick_mirror_file("file1", "file2")
    diff = Diff.from_commit(initial_commit, local_git_repo, file)
    assert diff == Diff(
        file,
        patch=textwrap.dedent(
            r"""
            diff --git a/file2 b/file2
            index 9c5956d15905570dbcad3d227a2ff446b4e06af5..eb9977164786d16df6a9a3e906a6cb25ecac9d99 100644
            --- a/file2
            +++ b/file2
            @@ -1 +1 @@
            -filev1
            \ No newline at end of file
            +filev2
            \ No newline at end of file
            """
        ).lstrip(),
        blob=b"filev1",
    )


@pytest.mark.typed
def test_diff_from_commit_changed_mode(local_git_repo: GitDir) -> None:
    initial_commit = add_commit(local_git_repo, dict(file="file"))
    os.chmod(
        local_git_repo / RelFile("file"),
        stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH,
    )
    file = quick_mirror_file("file")
    diff = Diff.from_commit(initial_commit, local_git_repo, file)
    assert diff == Diff(
        file,
        patch=textwrap.dedent(
            r"""
            diff --git a/file b/file
            old mode 100644
            new mode 100755
            +++ b/file
            --- /dev/null
            """
        ).lstrip(),
        blob=b"file",
    )


@pytest.mark.typed
def test_diff_from_commit_empty(local_git_repo: GitDir) -> None:
    initial_commit = add_commit(local_git_repo, dict(file1="file1"))
    add_commit(local_git_repo, dict(file1="file1"))
    file = quick_mirror_file("file1", "file2")
    diff = Diff.from_commit(initial_commit, local_git_repo, file)
    assert diff == Diff(
        file,
        patch="",
        blob=b"file1",
    )


@pytest.mark.parametrize(
    "file",
    [
        quick_mirror_file("empty"),
        quick_mirror_file("line_added"),
        quick_mirror_file("merged_cleanly"),
        quick_mirror_file("conflict"),
        quick_mirror_file("line_added", "rename"),
        quick_mirror_file("no_change", "empty"),
        quick_mirror_file("line_added", "nested/folder/new"),
        quick_mirror_file("change_mode.1", "no_change"),
    ],
)
def test_diff_apply_versioned_file(
    file: MirrorFile, test_data_path: AbsDir, snapshot: SnapshotAssertion, local_git_repo: GitDir
) -> None:
    test_data_path /= RelDir("merge")
    remote_path = GitDir(tempfile.mkdtemp(), check=False)
    if (test_data_path / file.source + Ext(".1")).exists():
        shutil.copy2(test_data_path / file.source + Ext(".1"), remote_path / file.source)
    else:
        shutil.copy2(test_data_path / file.source, remote_path / file.source)
    source_commit = add_commit(remote_path)
    if (test_data_path / file.source + Ext(".2")).exists():
        shutil.copy2(test_data_path / file.source + Ext(".2"), remote_path / file.source)
    else:
        shutil.copy2(test_data_path / file.source, remote_path / file.source)
    add_commit(remote_path)
    diff = Diff.from_commit(source_commit, remote_path, file)
    if (test_data_path / file.target).exists():
        (local_git_repo / file.target).path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(test_data_path / file.target, local_git_repo / file.target)
    diff.apply(local_git_repo)
    with open(local_git_repo / file.target) as f:
        assert f.read() == snapshot
