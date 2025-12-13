from __future__ import annotations

import contextlib
import filecmp
from multiprocessing import Process, Queue
import random
import time
from typing import TYPE_CHECKING, Self
from unittest import mock

import pytest

from .constants import MIRROR_LOCK, MIRROR_SEMAPHORE_EXTENSION
from .lock import FileSystemLock, FileSystemSemaphore
from .typed_path import AbsDir, AbsFile, PyFile, RelDir, RelFile

if TYPE_CHECKING:
    from _typeshed import SupportsWrite


@pytest.fixture
def tmp_lock_path(typed_tmp_path: AbsDir) -> AbsFile:
    return typed_tmp_path / MIRROR_LOCK


@pytest.fixture
def tmp_extra_lock_path(typed_tmp_path: AbsDir) -> AbsFile:
    return typed_tmp_path / (MIRROR_LOCK + MIRROR_SEMAPHORE_EXTENSION)


@pytest.fixture
def test_data_path(global_test_data_path: AbsDir) -> AbsDir:
    return global_test_data_path / RelDir("locking_tests")


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
    assert filecmp.cmp(tmp_lock_path, test_data_path / RelFile("expected_lock_file"))


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
        FileSystemLock.create(test_data_path / RelFile("existing_lock"))


@pytest.mark.typed
def test_create_new_file_created_in_race(tmp_lock_path: AbsFile) -> None:
    class MockFileSystemLock(FileSystemLock):
        @classmethod
        def acquire_non_blocking(cls, file: PyFile) -> Self | None:
            with open(tmp_lock_path, "w") as f:
                intercepted_lock = super().acquire_non_blocking(f)
                assert intercepted_lock
                return super().acquire_non_blocking(file)

    with pytest.raises(OSError):
        MockFileSystemLock.create(tmp_lock_path)


@pytest.mark.typed
def test_edit_file_does_not_exist(tmp_lock_path: AbsFile) -> None:
    with pytest.raises(FileNotFoundError):
        FileSystemLock.edit(tmp_lock_path)


@pytest.mark.typed
def test_edit_file(tmp_lock_path: AbsFile) -> None:
    tmp_lock_path.path.touch()
    lock = FileSystemLock.edit(tmp_lock_path)
    lock.file.write("success")  # test is writeable
    lock.file.read()  # test is readable


@pytest.mark.typed
def test_edit_file_in_race(tmp_lock_path: AbsFile) -> None:
    class MockFileSystemLock(FileSystemLock):
        @classmethod
        def acquire_non_blocking(cls, file: PyFile) -> Self | None:
            with open(tmp_lock_path, "w") as f:
                intercepted_lock = super().acquire_non_blocking(f)
                assert intercepted_lock
                return super().acquire_non_blocking(file)

    tmp_lock_path.path.touch()
    with pytest.raises(OSError):
        MockFileSystemLock.edit(tmp_lock_path)


@pytest.mark.typed
def test_file_system_semaphore_single_process(
    tmp_lock_path: AbsFile, tmp_extra_lock_path: AbsFile
) -> None:
    lock = FileSystemSemaphore.acquire(tmp_lock_path)
    lock.synchronize(tmp_extra_lock_path)
    lock.release()


@pytest.mark.typed
def test_file_system_semaphore_single_process_repeated(
    tmp_lock_path: AbsFile, tmp_extra_lock_path: AbsFile
) -> None:
    for _ in range(2):
        lock = FileSystemSemaphore.acquire(tmp_lock_path)
        lock.synchronize(tmp_extra_lock_path)
        lock.release()


@pytest.mark.parametrize("release_instruction_position", range(3))
def test_file_system_semaphore_single_process_interleaved(
    tmp_lock_path: AbsFile, tmp_extra_lock_path: AbsFile, release_instruction_position: int
) -> None:
    leader_lock = FileSystemSemaphore.acquire(tmp_lock_path)
    follower_lock = FileSystemSemaphore.acquire(tmp_lock_path)
    leader_lock.synchronize(tmp_extra_lock_path)
    if release_instruction_position == 0:
        leader_lock.release()
    follower_lock.synchronize(tmp_extra_lock_path)
    if release_instruction_position == 1:
        leader_lock.release()
    follower_lock.release()
    if release_instruction_position == 3:
        leader_lock.release()


def single_follower_process(
    semaphore_path: AbsFile,
    monitor_path: AbsFile,
) -> None:
    with mock.patch.object(FileSystemSemaphore, "TIMEOUT_SECONDS", 0.5):
        lock = FileSystemSemaphore.acquire(semaphore_path)
        lock.synchronize(monitor_path)
        lock.release()


@pytest.mark.slow
def test_file_system_semaphore_leader_crash(
    tmp_lock_path: AbsFile,
    tmp_extra_lock_path: AbsFile,
) -> None:
    follower = Process(
        target=single_follower_process,
        args=(tmp_lock_path, tmp_extra_lock_path),
    )
    with open(tmp_lock_path, "x"), open(tmp_extra_lock_path, "x"):
        ...
    leader_lock = FileSystemSemaphore.acquire(tmp_lock_path)
    follower.start()
    leader_lock.release()
    follower.join(1.0)
    if follower.is_alive():
        follower.kill()
        pytest.fail("Follower did not terminate")


def multi_follower_process(
    semaphore_path: AbsFile,
    monitor_path: AbsFile,
    data_path: AbsFile,
    queue: Queue[tuple[int, str]],
    idx: int,
) -> None:
    print(f"{idx}: pre-acquire")
    lock = FileSystemSemaphore.acquire(semaphore_path)
    print(f"{idx}: post-acquire")
    time.sleep(random.random())
    print(f"{idx}: pre-sync")
    lock.synchronize(monitor_path)
    print(f"{idx}: post-sync")
    with open(data_path) as f:
        data = f.read()
    time.sleep(random.random())
    print(f"{idx}: pre-release")
    lock.release()
    print(f"{idx}: post-release")
    queue.put((idx, data))


@pytest.mark.slow
@pytest.mark.parametrize("seed", range(3))
@pytest.mark.parametrize("num_followers", [1, 2, 4])
@pytest.mark.parametrize("release_early", [True, False])
def test_file_system_semaphore_multiple_processes(
    typed_tmp_path: AbsDir,
    tmp_lock_path: AbsFile,
    tmp_extra_lock_path: AbsFile,
    seed: int,
    num_followers: int,
    release_early: bool,
) -> None:
    random.seed(seed)
    data_path = typed_tmp_path / RelFile("data")
    queue: Queue[tuple[int, str]] = Queue()
    followers = [
        Process(
            target=multi_follower_process,
            args=(tmp_lock_path, tmp_extra_lock_path, data_path, queue, idx),
        )
        for idx in range(num_followers)
    ]
    with open(tmp_lock_path, "x"), open(tmp_extra_lock_path, "x"):
        ...
    leader_lock = FileSystemSemaphore.acquire(tmp_lock_path)
    for follower in followers:
        follower.start()
    time.sleep(random.random())
    with open(data_path, "x") as f:
        f.write("data")
    leader_lock.synchronize(tmp_extra_lock_path)
    if release_early:
        time.sleep(random.random())
        leader_lock.release()
    for follower in followers:
        follower.join(2.0)

    result = dict(queue.get_nowait() for _ in range(num_followers))
    assert result == {idx: "data" for idx in range(num_followers)}
