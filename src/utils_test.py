import random
from typing import Never, cast

import pytest

from .utils import all_unique, strict_not_none


@pytest.mark.parametrize("seed", range(3))
@pytest.mark.parametrize(
    "items, result",
    [
        # empty
        ([], True),
        # singleton
        ([1], True),
        # all unique
        ([1, 2, 3], True),
        # all same
        ([3, 3, 3], False),
        # some same
        ([1, 2, 8, 1], False),
    ],
)
def test_all_unique(seed: int, items: list[int], result: bool) -> None:
    if seed != 0:
        random.shuffle(items)
    assert all_unique(iter(items)) == result


def test_not_none_none_only() -> None:
    with pytest.raises(TypeError):
        _: Never = strict_not_none(None)


def test_not_none_not_none() -> None:
    x: int = strict_not_none(cast(int | None, 5))
    assert x == 5


def test_not_none_is_none() -> None:
    with pytest.raises(TypeError):
        _: int = strict_not_none(cast(int | None, None))


def test_not_none_not_none_type() -> None:
    x: int = strict_not_none(cast(int, 7))
    assert x == 7
