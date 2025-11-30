from collections.abc import Sequence
import os.path
from pathlib import Path
import re
from typing import Literal

import pytest

from .typed_path import AbsDir, AbsFile, Ext, RelDir, RelFile, Remote, TypedPath

PATH_TYPES: Sequence[type[TypedPath]] = [RelFile, AbsFile, RelDir, AbsDir]


def _make_path(type_: type[TypedPath], path: str | Path) -> TypedPath:
    path = Path(path)
    if issubclass(type_, AbsFile | AbsDir):
        path = path.absolute()
    return type_(path)


@pytest.fixture
def test_data_path(global_test_data_path: AbsDir) -> AbsDir:
    return global_test_data_path / RelDir("path_tests")


@pytest.mark.parametrize("left_type", PATH_TYPES)
@pytest.mark.parametrize("right_type", PATH_TYPES)
@pytest.mark.parametrize("left_name", ["folder", "file"])
@pytest.mark.parametrize("right_name", ["nested", "file"])
def test_typed_path_join(
    left_type: type[TypedPath], right_type: type[TypedPath], left_name: str, right_name: str
) -> None:
    left_path = _make_path(left_type, left_name)
    right_path = _make_path(right_type, right_name)

    expected_result: dict[tuple[type[TypedPath], type[TypedPath]], type[TypedPath]] = {
        (AbsDir, RelFile): AbsFile,
        (AbsDir, RelDir): AbsDir,
        (RelDir, RelFile): RelFile,
        (RelDir, RelDir): RelDir,
    }
    expected = expected_result.get((left_type, right_type))

    if expected is None:
        with pytest.raises(TypeError):
            left_path / right_path  # type: ignore [operator]
    else:
        assert left_path / right_path == _make_path(  # type: ignore [operator]
            expected, os.path.join(left_name, right_name)
        )


@pytest.mark.parametrize("path_type", PATH_TYPES)
@pytest.mark.parametrize(
    "name, exists, is_file, is_folder",
    [
        ("", True, False, True),
        ("exists", True, True, False),
        ("doesnotexist", False, False, False),
    ],
)
@pytest.mark.parametrize("property", ["exists", "is_file", "is_folder"])
def test_path_properties(
    path_type: type[TypedPath],
    name: str,
    property: Literal["exists", "is_file", "is_folder"],
    exists: bool,
    is_file: bool,
    is_folder: bool,
    test_data_path: AbsDir,
) -> None:
    path = _make_path(path_type, test_data_path.path / name)
    match property:
        case "exists":
            assert path.exists() == exists
        case "is_file":
            assert path.is_file() == is_file
        case "is_folder":
            assert path.is_folder() == is_folder


@pytest.mark.parametrize(
    "a, b, same",
    [
        # identical files
        ("a/b", "a/b", True),
        # identical urls
        (
            "https://github.com/George-Ogden/mypy-pytest.git",
            "https://github.com/George-Ogden/mypy-pytest.git",
            True,
        ),
        # equivalent files
        ("a/../b", "b/", True),
        # equivalent urls
        (
            "https://github.com/George-Ogden/mypy-pytest",
            "https://github.com/George-Ogden/mypy-pytest/",
            True,
        ),
        # different protocols
        (
            "git@github.com:George-Ogden/mypy-pytest.git",
            "https://github.com/George-Ogden/mypy-pytest/",
            False,
        ),
        # different urls
        (
            "https://bitbucket.com/George-Ogden/mypy-pytest",
            "https://github.com/George-Ogden/mypy-pytest",
            False,
        ),
        # different files
        (
            "a/b/c",
            "c/b/a",
            False,
        ),
    ],
)
def test_remote_hash(a: str, b: str, same: bool) -> None:
    assert (Remote(a).hash == Remote(b).hash) == same
    for name in a, b:
        pattern = r"^[a-z0-9]{1,200}$"
        assert re.match(pattern, Remote(name).hash, re.IGNORECASE)


@pytest.mark.parametrize("path_type", PATH_TYPES)
@pytest.mark.parametrize("path", ["basic.txt", "folder/.git/file_or_folder"])
@pytest.mark.parametrize("extension", [".tmp", ".bkp"])
def test_path_add(
    path_type: type[TypedPath],
    path: str,
    extension: str,
) -> None:
    file_types = {AbsFile, RelFile}
    left = path_type(path)
    right = Ext(extension)
    if path_type in file_types:
        assert left + right == path_type(path + extension)  # type: ignore [operator]
    else:
        with pytest.raises(TypeError):
            left + right  # type: ignore [operator]
