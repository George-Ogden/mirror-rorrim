from collections.abc import Hashable, Iterable
import typing
from typing import Any, Literal, TypeAliasType, overload


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


@overload
def strict_cast[T](type_: type[T], expr: Any, /) -> T: ...


@overload
def strict_cast(type_: object, expr: Any, /) -> Any: ...


def strict_cast(type_: object, expr: Any, /) -> Any:
    if isinstance(type_, TypeAliasType):
        return strict_cast(type_.__value__, expr)
    if typing.get_origin(type_) is Literal:
        return strict_literal_cast(strict_not_none(typing.get_args(type_)), expr)
    try:
        type_checks = isinstance(expr, type_)  # type: ignore
    except TypeError:
        ...
    else:
        if not type_checks:
            raise TypeError()
    return expr


def strict_literal_cast[T](types: tuple, expr: T, /) -> T:
    if expr in types:
        return expr
    raise TypeError()
