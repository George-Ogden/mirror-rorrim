from inline_snapshot import snapshot
from inline_snapshot._snapshot.undecided_value import UndecidedValue
import pytest
import yaml
from yaml.nodes import Node

from .config import MirrorFileConfig
from .config_parser import Parser, ParserError
from .typed_path import RelFile


def quick_mirror_file_config(source: str, target: str | None = None) -> MirrorFileConfig:
    if target is None:
        target = source
    return MirrorFileConfig(source=RelFile(source), target=RelFile(target))


@pytest.fixture
def yaml_node(raw_yaml: str) -> Node:
    return yaml.compose(raw_yaml)


@pytest.mark.parametrize(
    "raw_yaml, expected",
    [
        (
            # file with same name
            "filename.py",
            quick_mirror_file_config("filename.py"),
        ),
        (
            # file with different names
            "filename.py: filename2.py",
            quick_mirror_file_config("filename2.py", "filename.py"),
        ),
        (
            # wrong node type
            "[filename1.py, filename2.py]",
            snapshot(
                "An unexpected error occurred during parsing. <string>:1: Expected 'filename' or 'filename:filename'"
            ),
        ),
        (
            # filename that is trivially above root
            "../filename",
            snapshot(
                "An unexpected error occurred during parsing. <string>:1: The filename '../filename' goes out of the repository and is therefore not valid."
            ),
        ),
        (
            # filename that is non-trivially above root
            "folder/../../filename",
            snapshot(
                "An unexpected error occurred during parsing. <string>:1: The filename 'folder/../../filename' goes out of the repository and is therefore not valid."
            ),
        ),
        (
            # convoluted filename that is not above root
            "bar.py: folder/../file/../bar.py",
            quick_mirror_file_config("folder/../file/../bar.py", "bar.py"),
        ),
        (
            # filename in quotes
            "'folder/filename.txt'",
            quick_mirror_file_config("folder/filename.txt"),
        ),
        (
            # filenames in quotes
            "'folder/filename.txt': 'filename.txt'",
            quick_mirror_file_config("filename.txt", "folder/filename.txt"),
        ),
        (
            # json-style mapping
            "{'file': 'file'}",
            quick_mirror_file_config("file"),
        ),
    ],
)
def test_parse_file_config(yaml_node: Node, expected: MirrorFileConfig | str) -> None:
    parser = Parser(RelFile("<string>"))
    if isinstance(expected, str | UndecidedValue):
        with pytest.raises(ParserError) as e:
            parser.mirror_file_config_from_yaml(yaml_node)
        assert str(e.value) == expected
    else:
        assert parser.mirror_file_config_from_yaml(yaml_node) == expected
