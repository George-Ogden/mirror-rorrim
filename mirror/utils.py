import typing
from typing import Any, Literal, TypeAliasType, overload

from extra_types.type_utils import strict_not_none


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
