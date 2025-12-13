import random

import pytest

from .utils import all_unique


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
