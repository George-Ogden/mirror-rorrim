from pathlib import Path

import pytest

from .typed_path import AbsDir


@pytest.fixture
def typed_tmp_path(tmp_path: Path) -> AbsDir:
    return AbsDir(tmp_path)
