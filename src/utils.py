from collections.abc import Hashable, Iterable


def all_unique[T: Hashable](items: Iterable[T]) -> bool:
    seen = set()
    for i, x in enumerate(items, 1):
        seen.add(x)
        if len(seen) != i:
            return False
    return True
