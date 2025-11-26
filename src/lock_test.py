import pytest

from .constants import MIRROR_LOCK
from .lock import FileSystemLock
from .typed_path import AbsDir


@pytest.mark.typed
def test_locking_acquire_one_process(typed_tmp_path: AbsDir) -> None:
    with open((typed_tmp_path / MIRROR_LOCK), "x") as f:
        assert FileSystemLock.acquire_non_blocking(f)


@pytest.mark.typed
def test_locking_acquire_two_processes(typed_tmp_path: AbsDir) -> None:
    with open((typed_tmp_path / MIRROR_LOCK), "x") as f1:
        lock = FileSystemLock.acquire_non_blocking(f1)
        assert lock
        with open((typed_tmp_path / MIRROR_LOCK), "r+") as f2:
            assert not FileSystemLock.acquire_non_blocking(f2)


@pytest.mark.typed
def test_locking_acquire_release_two_processes_with_release(typed_tmp_path: AbsDir) -> None:
    with open((typed_tmp_path / MIRROR_LOCK), "x") as f1:
        lock = FileSystemLock.acquire_non_blocking(f1)
        assert lock
        with open((typed_tmp_path / MIRROR_LOCK), "r+") as f2:
            assert not FileSystemLock.acquire_non_blocking(f2)
        lock.release()

    with open((typed_tmp_path / MIRROR_LOCK), "r+") as f3:
        lock = FileSystemLock.acquire_non_blocking(f3)
        assert lock


@pytest.mark.typed
def test_locking_destructor_unlocks_lock(typed_tmp_path: AbsDir) -> None:
    file = open((typed_tmp_path / MIRROR_LOCK), "x")  # noqa: SIM115
    lock = FileSystemLock.acquire_non_blocking(file)
    del lock
    assert file.closed

    file = open((typed_tmp_path / MIRROR_LOCK), "r+")  # noqa: SIM115
    lock = FileSystemLock.acquire_non_blocking(file)
    assert lock
