from typing import Literal

import pytest

from .utils import strict_cast


def test_strict_cast_type() -> None:
    x: int | None = 5
    y: int = strict_cast(int, x)
    assert y == 5


def test_strict_cast_literal() -> None:
    x: int = 5
    y: Literal[5] = strict_cast(Literal[5], x)
    assert y == 5


def test_strict_cast_literal_fail() -> None:
    x: int = 5
    with pytest.raises(TypeError):
        _: Literal[5] = strict_cast(Literal[2, 4, 6], x)


def test_strict_cast_union() -> None:
    x: int | str | None = 5
    y: int | str = strict_cast(int | str, x)
    assert y == 5


def test_strict_cast_fail() -> None:
    x: int | str | None = 5
    with pytest.raises(TypeError):
        _: str | None = strict_cast(str | None, x)


type TypeAlias1 = int
type TypeAlias2 = TypeAlias1


def test_strict_cast_typealias() -> None:
    x: int = 4
    y: TypeAlias2 = strict_cast(TypeAlias2, x)
    assert x == y


def test_strict_cast_typealias_fail() -> None:
    x: str = "4"
    with pytest.raises(TypeError):
        _: TypeAlias2 = strict_cast(TypeAlias2, x)
