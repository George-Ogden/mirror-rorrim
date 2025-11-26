from collections.abc import Callable
from dataclasses import dataclass, field
import functools
import inspect
import os.path

from yaml import MappingNode, Node, ScalarNode

from .config import MirrorFileConfig
from .typed_path import AbsFile, RelFile


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
            position = f"{position}:{self.context.node.start_mark.line + 1}"
        return position

    def __str__(self) -> str:
        return f"An unexpected error occurred during parsing. {self.position}: {self.msg}"


@dataclass
class Parser:
    filename: AbsFile | RelFile
    _node: Node = field(
        init=False, repr=False, hash=False, compare=False, default=Node("", None, None, None)
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
            previous_node = self._node
            binding = signature.bind(*args, **kwargs)
            # Update the variable node if it exists as an argument.
            self._node = binding.arguments.get("node", previous_node)
            try:
                return method(*args, **kwargs)
            finally:
                self._node = previous_node

        return wrapper

    @property
    def context(self) -> Context:
        return Context(self.filename, self._node)

    def _relfile_from_scalar_node(self, node: ScalarNode) -> RelFile:
        file = RelFile(node.value)
        # pathlib.Path.resolve uses the filesystem, which we don't want
        if os.path.normpath(file.path).startswith(".."):
            raise ParserError(
                f"The filename {file!s} goes out of the repository and is therefore not valid.",
                self.context,
            )
        return file

    def mirror_file_config_from_yaml(self, node: Node) -> MirrorFileConfig:
        match node:
            case ScalarNode() if isinstance(node.value, str):
                file = self._relfile_from_scalar_node(node)
                return MirrorFileConfig(source=file, target=file)
            case MappingNode():
                match node.value:
                    case [(ScalarNode() as target_node, ScalarNode() as source_node)]:
                        return MirrorFileConfig(
                            source=self._relfile_from_scalar_node(source_node),
                            target=self._relfile_from_scalar_node(target_node),
                        )
        raise ParserError(context=self.context, msg="Expected 'filename' or 'filename:filename'")
