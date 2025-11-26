from pathlib import Path

import pytest

from .constants import MIRROR_LOCK
from .typed_path import AbsDir, AbsFile


@pytest.fixture
def test_data_path() -> AbsDir:
    return AbsDir(Path(__file__).absolute().parent.parent / "test_data")


@pytest.fixture
def typed_tmp_path(tmp_path: Path) -> AbsDir:
    return AbsDir(tmp_path)


@pytest.fixture
def tmp_lock_path(typed_tmp_path: AbsDir) -> AbsFile:
    return typed_tmp_path / MIRROR_LOCK
