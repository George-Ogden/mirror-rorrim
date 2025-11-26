from __future__ import annotations

import contextlib
import filecmp
from typing import TYPE_CHECKING, Self

import pytest

from .lock import FileSystemLock
from .typed_path import AbsDir, AbsFile, PyFile, RelFile

if TYPE_CHECKING:
    from _typeshed import SupportsWrite


@pytest.mark.typed
def test_acquire_one_process(tmp_lock_path: AbsFile) -> None:
    with open(tmp_lock_path, "x") as f:
        assert FileSystemLock.acquire_non_blocking(f)


@pytest.mark.typed
def test_acquire_two_processes(tmp_lock_path: AbsFile) -> None:
    with open(tmp_lock_path, "x") as f1:
        lock = FileSystemLock.acquire_non_blocking(f1)
        assert lock
        with open(tmp_lock_path, "r+") as f2:
            assert not FileSystemLock.acquire_non_blocking(f2)


@pytest.mark.typed
def test_acquire_release_two_processes_with_release(tmp_lock_path: AbsFile) -> None:
    with open(tmp_lock_path, "x") as f1:
        lock = FileSystemLock.acquire_non_blocking(f1)
        assert lock
        with open(tmp_lock_path, "r+") as f2:
            assert not FileSystemLock.acquire_non_blocking(f2)
        lock.release()

    with open(tmp_lock_path, "r+") as f3:
        lock = FileSystemLock.acquire_non_blocking(f3)
        assert lock


@pytest.mark.typed
def test_locking_destructor_unlocks_lock(tmp_lock_path: AbsFile) -> None:
    file = open(tmp_lock_path, "x")  # noqa: SIM115
    lock = FileSystemLock.acquire_non_blocking(file)
    del lock
    assert file.closed

    file = open(tmp_lock_path, "r+")  # noqa: SIM115
    lock = FileSystemLock.acquire_non_blocking(file)
    assert lock


@pytest.mark.typed
def test_unlock(tmp_lock_path: AbsFile, test_data_path: AbsDir) -> None:
    class SuccessDumper:
        def dump(self, f: SupportsWrite[str]) -> None:
            f.write("success\n")

    file = open(tmp_lock_path, "w")  # noqa: SIM115
    lock = FileSystemLock.acquire_non_blocking(file)
    assert lock
    lock.unlock(SuccessDumper())

    assert file.closed
    assert filecmp.cmp(tmp_lock_path, test_data_path / RelFile("locking_tests/expected_lock_file"))


@pytest.mark.typed
def test_unlock_failed_write(tmp_lock_path: AbsFile) -> None:
    class FailureDumper:
        def dump(self, f: SupportsWrite[str]) -> None:
            raise RuntimeError()

    file = open(tmp_lock_path, "w")  # noqa: SIM115
    lock = FileSystemLock.acquire_non_blocking(file)
    assert lock

    with contextlib.suppress(Exception):
        lock.unlock(FailureDumper())

    assert file.closed


@pytest.mark.typed
def test_create_new_file(tmp_lock_path: AbsFile) -> None:
    lock = FileSystemLock.create(tmp_lock_path)
    lock.file.write("success")  # test is writeable


@pytest.mark.typed
def test_create_new_file_exists_already(test_data_path: AbsDir) -> None:
    with pytest.raises(FileExistsError):
        FileSystemLock.create(test_data_path / RelFile("locking_tests/existing_lock"))


@pytest.mark.typed
def test_create_new_file_created_in_race(tmp_lock_path: AbsFile) -> None:
    class MockFileSystemLock(FileSystemLock):
        @classmethod
        def acquire_non_blocking(cls, file: PyFile) -> Self | None:
            with open(tmp_lock_path, "w") as f:
                intercepted_lock = super().acquire_non_blocking(f)
                assert intercepted_lock
                return super().acquire_non_blocking(file)

    with pytest.raises(FileExistsError):
        MockFileSystemLock.create(tmp_lock_path)
