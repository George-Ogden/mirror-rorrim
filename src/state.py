from __future__ import annotations

from collections.abc import Sequence
import dataclasses
from dataclasses import dataclass
import os
from pathlib import Path
import re
import typing
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, Self, cast

import yaml
from yaml import MappingNode, Node, ScalarNode, SequenceNode, YAMLError
from yaml.constructor import ConstructorError

from .typed_path import Commit, RelFile, Remote

if TYPE_CHECKING:
    from _typeshed import DataclassInstance, SupportsRead, SupportsWrite


class ReadableState(Protocol):
    @classmethod
    def load(cls, f: SupportsRead[str]) -> Self: ...


class WriteableState(Protocol):
    def dump(self, f: SupportsWrite[str]) -> None: ...


class ReadWriteableState(ReadableState, WriteableState, Protocol): ...


class AutoState(yaml.YAMLObject):
    yaml_tag = None

    def dump(self, f: SupportsWrite[str]) -> None:
        f.write(yaml.safe_dump(self.representation, default_flow_style=False))

    @classmethod
    def load(cls, f: SupportsRead[str]) -> Self:
        try:
            return cls.construct(cls, yaml.compose(f))
        except YAMLError as e:
            raise YAMLError("Unable to load data from lock file.") from e

    @classmethod
    def represent(cls, obj: Any) -> Any:
        match obj:
            case _ if dataclasses.is_dataclass(obj):
                try:
                    [field] = dataclasses.fields(obj)
                except ValueError:
                    return {
                        field.name: cls.represent(getattr(obj, field.name))
                        for field in dataclasses.fields(obj)
                    }
                return cls.represent(getattr(obj, field.name))
            case list() | set() | tuple():
                return [cls.represent(sub_obj) for sub_obj in obj]
            case os.PathLike():
                return os.fspath(obj)
            case str():
                return obj
        raise TypeError()

    @property
    def representation(self) -> Any:
        return self.represent(self)

    @classmethod
    def construct[T](cls, obj_cls: type[T] | str, node: Node) -> T:
        if dataclasses.is_dataclass(obj_cls):
            return cls._construct_dataclass(obj_cls, node)
        if cls.is_cls(obj_cls, str):
            return cast(T, cls._construct_str(node))
        if cls.is_cls(obj_cls, Path):
            return cast(T, Path(cls.construct(str, node)))
        if cls.is_cls(typing.get_origin(obj_cls), Sequence):
            return cls._construct_sequence(cast(type[T], obj_cls), node)  # type: ignore[type-var]
        if isinstance(obj_cls, str):
            return cls._construct_named_cls(obj_cls, node)
        raise ConstructorError()

    @classmethod
    def _construct_dataclass[T: DataclassInstance](cls, obj_cls: type[T], node: Node) -> T:
        fields = dataclasses.fields(obj_cls)
        try:
            [field] = fields
        except ValueError:
            if isinstance(node, MappingNode):
                node_values = {cls._construct_str(key): value for key, value in node.value}
                if node_values.keys() == {field.name for field in fields}:
                    return obj_cls(
                        **{
                            field.name: cls.construct(field.type, node_values[field.name])
                            for field in fields
                        }
                    )
            raise ConstructorError() from None
        return obj_cls(**{field.name: cls.construct(field.type, node)})

    @classmethod
    def _construct_str(cls, node: Node) -> str:
        if isinstance(node, ScalarNode) and isinstance(node.value, str):
            return node.value
        raise ConstructorError()

    @classmethod
    def _construct_sequence[T: Sequence](cls, obj_cls: type[T], node: Node) -> T:
        [item_cls] = typing.get_args(obj_cls)
        if isinstance(node, SequenceNode):
            return cast(T, [cls.construct(item_cls, item_node) for item_node in node.value])
        raise ConstructorError()

    @classmethod
    def _construct_named_cls(cls, type_name: str, node: Node) -> Any:
        return cls.construct(cls._named_type(type_name), node)

    @classmethod
    def _named_type(cls, type_name: str) -> type:
        name, arg = cls._type_origin_and_arg(type_name)
        return cls._lookup_type(name, arg)

    @classmethod
    def _type_origin_and_arg(cls, type_name: str) -> tuple[str, str]:
        match = re.match(r"^(.*?)(\[(.*)\]|)$", type_name)
        if match is None:
            raise ConstructorError()
        name, param = match.group(1), match.group(3)
        return name, param

    @classmethod
    def _lookup_type(cls, type_name: str, param_name: str) -> type:
        named_cls = globals()[type_name]
        if param_name:
            named_cls = named_cls[globals()[param_name]]
        return named_cls

    @classmethod
    def is_cls(cls, obj_cls: type | str | None, expected_cls: type) -> bool:
        return obj_cls is not None and (obj_cls is expected_cls or obj_cls == expected_cls.__name__)


@dataclass(frozen=True, slots=True)
class MirrorRepoState(AutoState):
    source: Remote
    commit: Commit
    files: Sequence[RelFile]


@dataclass(frozen=True, slots=True)
class MirrorState(AutoState):
    LOCK_COMMENT: ClassVar[str] = (
        "DANGER: EDIT AT YOUR OWN RISK. Track this file in version control so that others can sync files correctly."
    )
    repos: Sequence[MirrorRepoState]

    def dump(self, f: SupportsWrite[str]) -> None:
        f.write(f"# {self.LOCK_COMMENT}\n")
        AutoState.dump(self, f)
