import sys
import typing
from typing import Any, Literal, TypeAliasType

from extra_types.type_utils import strict_cast as original_strict_cast
from extra_types.type_utils import strict_not_none

if sys.version_info >= (3, 15):
    from typing import TypeForm
else:
    from typing_extensions import TypeForm


def strict_cast[T](type_: TypeForm[T], expr: Any, /) -> T:
    if isinstance(type_, TypeAliasType):
        return strict_cast(type_.__value__, expr)  # type: ignore[unreachable]
    if typing.get_origin(type_) is Literal:
        return strict_literal_cast(strict_not_none(typing.get_args(type_)), expr)
    return original_strict_cast(type_, expr)


def strict_literal_cast[T](types: tuple, expr: T, /) -> T:
    if expr in types:
        return expr
    raise TypeError()
