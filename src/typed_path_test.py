from collections.abc import Sequence
import os.path
from pathlib import Path

import pytest

from .typed_path import AbsDir, AbsFile, RelDir, RelFile, TypedPath

PATH_TYPES: Sequence[type[TypedPath]] = [RelFile, AbsFile, RelDir, AbsDir]


def _make_path(type_: type[TypedPath], name: str) -> TypedPath:
    path = Path(name)
    if issubclass(type_, AbsFile | AbsDir):
        path = path.absolute()
    return type_(path)


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
