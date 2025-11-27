from pathlib import Path

import pytest

from .config_parser import Parser
from .mirror import Mirror
from .test_utils import quick_mirror, quick_mirror_repo
from .typed_path import AbsDir, RelFile


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
