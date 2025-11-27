import tempfile

import pytest

from .githelper import GitHelper
from .test_utils import setup_repo
from .typed_path import AbsDir, RelFile, Remote


def local_remote_clone_test_case() -> tuple[str, list[str]]:
    files = ["folder/file", "unusually_named.file"]
    path = tempfile.mkdtemp()
    setup_repo(path, dict.fromkeys(files))
    return path, files


@pytest.mark.parametrize(
    "remote, expected_files",
    [
        (
            # HTTPS remote
            "https://github.com/George-Ogden/dbg",
            ["_debug/__init__.py", "debug/__init__.py"],
        ),
        (
            # SSH remote
            "git@github.com:George-Ogden/pytest-dbg.git",
            ["src/plugin.py"],
        ),
        local_remote_clone_test_case(),
    ],
)
def test_clone_remote(remote: str, expected_files: list[str], typed_tmp_path: AbsDir) -> None:
    GitHelper.clone(Remote(remote), typed_tmp_path)
    for file in expected_files:
        assert (typed_tmp_path / RelFile(file)).exists()
