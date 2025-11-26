from collections.abc import Callable, Collection
from dataclasses import dataclass, field
import difflib
import functools
import inspect
import os.path
from types import NoneType
from typing import Any, NoReturn, cast

from yaml import MappingNode, Node, ScalarNode, SequenceNode

from .config import MirrorFileConfig, MirrorRepoConfig
from .typed_path import AbsFile, RelFile, Remote


@dataclass(frozen=True, slots=True)
class Context:
    filename: RelFile | AbsFile
    node: Node


@dataclass(frozen=True, slots=True)
class ParserError(Exception):
    msg: str
    context: Context

    @property
    def position(self) -> str:
        position = str(self.context.filename.path)
        if self.context.node.start_mark is not None:
            position = f"{position}:{self.context.node.start_mark.line + 1}:{self.context.node.start_mark.column + 1}"
        return position

    def __str__(self) -> str:
        return f"An unexpected error occurred during parsing @ {self.position}: {self.msg}"


@dataclass
class Parser:
    filename: AbsFile | RelFile
    _node: Node = field(
        init=False, repr=False, hash=False, compare=False, default=Node("", None, None, None)
    )
    _parsed_files: dict[str, Node] = field(
        init=False, repr=False, hash=False, compare=False, default_factory=dict
    )
    _visited_nodes: set[int] = field(
        init=False, repr=False, hash=False, compare=False, default_factory=set
    )

    def __post_init__(self) -> None:
        self._wrap_methods()

    def _wrap_methods(self) -> None:
        for attr in dir(self):
            method = getattr(self, attr)
            if not attr.startswith("__") and inspect.ismethod(method):
                setattr(self, attr, self._context_wrap(method))

    def _context_wrap[**P, R](self, method: Callable[P, R]) -> Callable[P, R]:
        signature = inspect.signature(method, eval_str=False)

        @functools.wraps(method)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            binding = signature.bind(*args, **kwargs)
            node = binding.arguments.get("node")
            if node is None or node is self._node:
                return method(*args, **kwargs)
            if id(node) in self._visited_nodes:
                self.fail("recursive reference detected.", node=node)
            self._visited_nodes.add(id(node))
            previous_node = self._node
            self._node = node
            try:
                return method(*args, **kwargs)
            finally:
                self._node = previous_node
                self._visited_nodes.remove(id(node))

        return wrapper

    @property
    def context(self) -> Context:
        return Context(self.filename, self._node)

    def fail(self, message: str, *, node: Node | None = None) -> NoReturn:
        error = ParserError(message, self.context if node is None else Context(self.filename, node))
        raise error

    def type_of(self, node: Node) -> str:
        match node:
            case ScalarNode():
                match node.value:
                    case "":
                        return "empty string"
                    case str():
                        return "string"
                    case int():
                        return "integer"
                    case float():
                        return "float"
                    case NoneType():
                        return "null"
                    case _:
                        return type(node.value).__name__
            case SequenceNode():
                return "sequence"
            case MappingNode():
                return "mapping"
            case _:
                return "unknown"

    def _relfile_from_scalar_node(self, node: ScalarNode) -> RelFile:
        file = RelFile(node.value)
        # pathlib.Path.resolve uses the filesystem, which could have unwanted links.
        normpath = file.normpath
        if normpath.startswith(".."):
            return self.fail(
                f"the filename {node.value!r} goes out of the repository and is therefore not valid."
            )
        if normpath in (".", ""):
            return self.fail(
                f"the filename {node.value!r} points to the root of the repository and is therefore not valid."
            )
        return file

    def _check_duplicate_file(self, file_config: MirrorFileConfig, node: Node) -> None:
        normpath = file_config.target.normpath
        if existing_node := self._parsed_files.get(normpath):
            line_details = (
                ""
                if existing_node.start_mark is None
                else f"; already define on line {existing_node.start_mark.line + 1}"
            )
            self.fail(f"duplicate file {file_config.target}{line_details}.", node=node)
        self._parsed_files[normpath] = node

    def parse_mirror_file_config(self, node: Node) -> MirrorFileConfig:
        file_config = None
        match node:
            case ScalarNode() if isinstance(node.value, str):
                file = self._relfile_from_scalar_node(node)
                file_config = MirrorFileConfig(source=file, target=file)
            case MappingNode():
                match node.value:
                    case [(ScalarNode() as target_node, ScalarNode() as source_node)]:
                        file_config = MirrorFileConfig(
                            source=self._relfile_from_scalar_node(source_node),
                            target=self._relfile_from_scalar_node(target_node),
                        )
        if file_config is None:
            self.fail(f"expected filename as a string or single mapping, got {self.type_of(node)}.")
        self._check_duplicate_file(file_config, node)
        return file_config

    def parse_string_key[T: str](self, node: Node, options: Collection[T]) -> T:
        match node:
            case ScalarNode() if isinstance(key := node.value, str):
                if key in options:
                    return cast(T, key)
                suggestions = difflib.get_close_matches(key, possibilities=options, n=1)
                if suggestions:
                    [suggestion] = suggestions
                    message = f"invalid key {key!r}, did you mean {suggestion!r}?"
                else:
                    message = f"mapping key should be one of {list(options)!r}, got {key!r}."
                return self.fail(message)
        return self.fail(f"expected a string as the key, got {self.type_of(node)}.")

    def parse_remote(self, node: Node) -> Remote:
        match node:
            case ScalarNode() if isinstance(node.value, str):
                if os.path.normpath(node.value) == ".":
                    self.fail(
                        f"remote {node.value!r} points to the same repository, which is not allowed."
                    )
                return Remote(node.value)
        return self.fail(f"expected remote as a string, got {self.type_of(node)}.")

    def parse_mirror_file_configs(self, node: Node) -> list[MirrorFileConfig]:
        match node:
            case SequenceNode():
                if len(node.value) == 0:
                    self.fail("file list is empty.")
                return [self.parse_mirror_file_config(node) for node in node.value]
        return self.fail(f"expected sequence of files, got {self.type_of(node)}.")

    def parse_mapping[T](
        self,
        node: Node,
        subparsers: dict[str, Callable[[Node], Any]],
        combine: Callable[..., T],
    ) -> T:
        results = {}
        match node:
            case MappingNode():
                key_node: Node
                value_node: Node
                for key_node, value_node in node.value:
                    key = self.parse_string_key(key_node, options=subparsers.keys())
                    sub_parser = subparsers[key]
                    if key in results:
                        return self.fail(f"duplicate key {key!r} in mapping.", node=key_node)
                    results[key] = sub_parser(value_node)
        for key in subparsers.keys():
            if key not in results.keys():
                return self.fail(f"mapping is missing key {key!r}.")
        return combine(**results)

    def parse_mirror_repo_config(self, node: Node) -> MirrorRepoConfig:
        return self.parse_mapping(
            node,
            subparsers=dict(source=self.parse_remote, files=self.parse_mirror_file_configs),
            combine=MirrorRepoConfig,
        )
