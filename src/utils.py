from collections.abc import Hashable, Iterable


def all_unique[T: Hashable](items: Iterable[T]) -> bool:
    seen = set()
    for i, x in enumerate(items, 1):
        seen.add(x)
        if len(seen) != i:
            return False
    return True


def strict_not_none[T](not_none: T | None, /) -> T:
    if not_none is None:
        raise TypeError()
    return not_none
