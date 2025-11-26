import textwrap

from inline_snapshot import snapshot
from inline_snapshot._snapshot.undecided_value import UndecidedValue
import pytest
import yaml
from yaml.nodes import Node

from .config import MirrorFileConfig, MirrorRepoConfig
from .config_parser import Parser, ParserError
from .typed_path import RelFile, Remote


def quick_mirror_file_config(source: str, target: str | None = None) -> MirrorFileConfig:
    if target is None:
        target = source
    return MirrorFileConfig(source=RelFile(source), target=RelFile(target))


def quick_mirror_repo_config(source: str, files: list[tuple[str, str] | str]) -> MirrorRepoConfig:
    return MirrorRepoConfig(
        source=Remote(source),
        files=[
            quick_mirror_file_config(*file)
            if isinstance(file, tuple)
            else quick_mirror_file_config(file)
            for file in files
        ],
    )


@pytest.fixture
def yaml_node(raw_yaml: str) -> Node:
    raw_yaml = textwrap.dedent(raw_yaml).strip()
    return yaml.compose(raw_yaml, Loader=yaml.SafeLoader)


def _test_parse_body(
    yaml_node: Node, expected: MirrorFileConfig | MirrorRepoConfig | str, method_name: str
) -> None:
    parser = Parser(RelFile("<string>"))
    method = getattr(parser, method_name)
    if isinstance(expected, str | UndecidedValue):
        with pytest.raises(ParserError) as e:
            method(yaml_node)
        assert str(e.value) == expected
        assert str(e.value)[-1] in ".?"
    else:
        assert method(yaml_node) == expected


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
                "An unexpected error occurred during parsing @ <string>:1:1: expected filename as a string or single mapping, got sequence."
            ),
        ),
        (
            # filename that is trivially above root
            "../filename",
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:1: the filename '../filename' goes out of the repository and is therefore not valid."
            ),
        ),
        (
            # filename that is non-trivially above root
            "folder/../../filename",
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:1: the filename 'folder/../../filename' goes out of the repository and is therefore not valid."
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
        (
            # empty file mapping
            "''",
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:1: the filename '' points to the root of the repository and is therefore not valid."
            ),
        ),
        (
            # root folder
            ".",
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:1: the filename '.' points to the root of the repository and is therefore not valid."
            ),
        ),
    ],
)
def test_parse_file_config(yaml_node: Node, expected: MirrorFileConfig | str) -> None:
    _test_parse_body(yaml_node, expected, method_name="parse_mirror_file_config")


@pytest.mark.parametrize(
    "raw_yaml, expected",
    [
        (
            # two valid files
            """
            source: 'https://github.com/repo/awesome'
            files:
                - filename
                - copied: original
            """,
            quick_mirror_repo_config(
                "https://github.com/repo/awesome", ["filename", ("original", "copied")]
            ),
        ),
        (
            # invalid remote
            """
            source: {}
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:9: expected remote as a string, got mapping."
            ),
        ),
        (
            # invalid key
            """
            []: []
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:1: expected a string as the key, got sequence."
            ),
        ),
        (
            # invalid file config
            """
            source: valid-source
            files:
                - ['not correct']
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:3:7: expected filename as a string or single mapping, got sequence."
            ),
        ),
        (
            # invalid file configs
            """
            source: valid-source
            files: single-file
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:2:8: expected sequence of files, got string."
            ),
        ),
        (
            # consecutive mappings
            """
            source: 'https://github.com/repo/awesome'
            files:
                - file1: file1
                - file2: file2
                - copied: original
                - bar: foo
            """,
            quick_mirror_repo_config(
                "https://github.com/repo/awesome",
                ["file1", "file2", ("original", "copied"), ("foo", "bar")],
            ),
        ),
        (
            # nested mapping
            """
            source: 'https://github.com/repo/awesome'
            files:
                file1:
                    - mapping: foo
                    - file2: file2
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:3:5: expected sequence of files, got mapping."
            ),
        ),
        (
            # extra key
            """
            source: local
            files:
                - file 1
            extra: unknown
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:4:1: mapping key should be one of ['source', 'files'], got 'extra'."
            ),
        ),
        (
            # extra key as typo
            """
            source: local
            flies:
                - file 1
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:2:1: invalid key 'flies', did you mean 'files'?"
            ),
        ),
        (
            # missing source
            """
            files:
                - file 1
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:1: mapping is missing key 'source'."
            ),
        ),
        (
            # missing files
            """
            source: magic sauce
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:1: mapping is missing key 'files'."
            ),
        ),
        (
            # duplicate key
            """
            source: magic sauce
            source: hot sauce
            files:
                - filename
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:2:1: duplicate key 'source' in mapping."
            ),
        ),
        (
            # no files
            """
            source: ketchup
            files: []
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:2:8: file list is empty."
            ),
        ),
        (
            # duplicated file
            """
            files:
                - file1
                - file2: file3
                - file3
                - file4
                - file2
                - file1
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:6:7: duplicate file 'file2'; already define on line 3."
            ),
        ),
        (
            # duplicated file indirectly
            """
            files:
                - file1
                - file2: file3
                - file3
                - file4
                - folder/file2
                - folder/../file1
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:7:7: duplicate file 'folder/../file1'; already define on line 2."
            ),
        ),
        (
            # empty files
            """
            files:
            source: valid-source
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:7: expected sequence of files, got empty string."
            ),
        ),
        (
            # empty repo
            """
            source: ""
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:9: remote '' points to the same repository, which is not allowed."
            ),
        ),
        (
            # same repo
            """
            source: "."
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:9: remote '.' points to the same repository, which is not allowed."
            ),
        ),
        (
            # indirect same repo
            """
            source: "folder/.."
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:9: remote 'folder/..' points to the same repository, which is not allowed."
            ),
        ),
        (
            # canonical form
            """
            ---
            !!map {
            ? !!str "files"
            : !!seq [
                !!str "filename",
            ],
            ? !!str "source"
            : !!str "source",
            }
            """,
            quick_mirror_repo_config("source", ["filename"]),
        ),
        (
            # safe load
            """
            !!python/object/apply:builtins.exec
            args: ['assert False']
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:2:1: mapping key should be one of ['source', 'files'], got 'args'."
            ),
        ),
        (
            # valid reference
            """
            source: &R
                repo
            files: [*R]
            """,
            quick_mirror_repo_config("repo", ["repo"]),
        ),
        (
            # cyclic reference
            """
            files: &R
                [*R]
            source: *R
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:8: expected filename as a string or single mapping, got sequence."
            ),
        ),
    ],
)
def test_parse_repo_config(yaml_node: Node, expected: MirrorRepoConfig | str) -> None:
    _test_parse_body(yaml_node, expected, method_name="parse_mirror_repo_config")
