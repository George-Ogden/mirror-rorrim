from pathlib import Path
import tempfile

import pytest
from syrupy.assertion import SnapshotAssertion

from .config_parser import Parser
from .constants import MIRROR_LOCK
from .mirror import Mirror
from .test_utils import add_commit, quick_mirror, quick_mirror_repo
from .typed_path import AbsDir, RelDir, RelFile


@pytest.fixture
def test_data_path(global_test_data_path: AbsDir) -> AbsDir:
    return global_test_data_path / RelDir("mirror_tests")


@pytest.mark.parametrize(
    "config_name, expected",
    [
        (
            "single",
            quick_mirror(
                [quick_mirror_repo("https://github.com/George-Ogden/dbg", ["pyproject.toml"])]
            ),
        ),
        (
            "multiple",
            quick_mirror(
                [
                    quick_mirror_repo(
                        "https://github.com/George-Ogden/mypy-pytest",
                        ["pyproject.toml", ("requirements-dev.txt", "requirements.txt")],
                    ),
                    quick_mirror_repo(
                        "git@github.com:George-Ogden/actions.git",
                        [
                            (
                                ".github/workflows/python-release.yaml",
                                ".github/workflows/release.yaml",
                            ),
                            (
                                ".github/workflows/python-test.yaml",
                                ".github/workflows/test.yaml",
                            ),
                            (
                                ".github/workflows/lint.yaml",
                                ".github/workflows/lint.yaml",
                            ),
                        ],
                    ),
                ]
            ),
        ),
    ],
)
def test_mirror_from_config(
    config_name: str, expected: Mirror, global_test_data_path: AbsDir
) -> None:
    config_path = global_test_data_path / RelFile(Path("config_tests") / f"{config_name}.yaml")
    config = Parser.parse_file(config_path)
    assert Mirror.from_config(config) == expected


def multiple_repos_local_test_case() -> Mirror:
    remote1 = tempfile.mkdtemp()
    remote2 = tempfile.mkdtemp()
    commit1 = add_commit(remote1, dict(file1="file1", file2="file2"))
    commit2 = add_commit(remote2, dict(file3="file3", file4="file4", file5="file5"))
    mirror = quick_mirror(
        [
            quick_mirror_repo(remote1, ["file1", "file2", ("file2", "file3")]),
            quick_mirror_repo(remote2, ["file4", "file5", ("file3", "file6")]),
        ]
    )
    object.__setattr__(
        mirror,
        "__replacement__",
        {remote1: "remote1", remote2: "remote2", commit1: "commit1", commit2: "commit2"},
    )
    return mirror


@pytest.mark.parametrize(
    "mirror, test_name",
    [
        (
            quick_mirror(
                [quick_mirror_repo("https://github.com/George-Ogden/dbg", ["pyproject.toml"])]
            ),
            "single",
        ),
        (multiple_repos_local_test_case(), multiple_repos_local_test_case.__name__),
    ],
)
def test_mirror_state(mirror: Mirror, snapshot: SnapshotAssertion, typed_tmp_path: AbsDir) -> None:
    mirror.checkout_all()
    with open(typed_tmp_path / RelFile(MIRROR_LOCK), "a+") as f:
        mirror.state.dump(f)
        f.seek(0)
        contents = f.read()
        if hasattr(mirror, "__replacement__"):
            for search, replacement in mirror.__replacement__.items():  # type: ignore [attr]
                contents = contents.replace(search, replacement)
        assert contents == snapshot
