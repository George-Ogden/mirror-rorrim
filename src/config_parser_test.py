import textwrap

from inline_snapshot import snapshot
from inline_snapshot._snapshot.undecided_value import UndecidedValue
import pytest
import yaml
from yaml import Node, YAMLError

from .config import MirrorConfig, MirrorFileConfig, MirrorRepoConfig
from .config_parser import Parser, ParserError
from .typed_path import AbsDir, RelFile, Remote


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


def quick_mirror_config(repos: list[MirrorRepoConfig]) -> MirrorConfig:
    return MirrorConfig(repos)


@pytest.fixture
def yaml_node(raw_yaml: str) -> Node:
    raw_yaml = textwrap.dedent(raw_yaml).strip()
    return yaml.compose(raw_yaml, Loader=yaml.SafeLoader)


def _test_parse_body(
    yaml_node: Node,
    expected: MirrorFileConfig | MirrorRepoConfig | MirrorConfig | str,
    method_name: str,
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
                "An unexpected error occurred during parsing @ <string>:1:1: repo mapping is missing the key 'source'."
            ),
        ),
        (
            # missing files
            """
            source: magic sauce
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:1: repo mapping is missing the key 'files'."
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
                "An unexpected error occurred during parsing @ <string>:2:8: files list is empty."
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
                "An unexpected error occurred during parsing @ <string>:6:7: duplicate file 'file2'; already used on line 3."
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
                "An unexpected error occurred during parsing @ <string>:7:7: duplicate file 'folder/../file1'; already used on line 2."
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
        (
            # wrong type
            """
            word
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:1: expected repo mapping, got string."
            ),
        ),
    ],
)
def test_parse_repo_config(yaml_node: Node, expected: MirrorRepoConfig | str) -> None:
    _test_parse_body(yaml_node, expected, method_name="parse_mirror_repo_config")


@pytest.mark.parametrize(
    "raw_yaml, expected",
    [
        (
            # one repository, one file
            """
            repos:
              - source: source1
                files: [file1]
            """,
            quick_mirror_config([quick_mirror_repo_config("source1", ["file1"])]),
        ),
        (
            # no repositories
            """
            repos: []
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:8: repos list is empty."
            ),
        ),
        (
            # many files across many repos
            """
            repos:
              - source: source1
                files: [file1, file2]
              - source: source2
                files:
                  - file3
                  - file4
                  - file5
            """,
            quick_mirror_config(
                [
                    quick_mirror_repo_config("source1", ["file1", "file2"]),
                    quick_mirror_repo_config("source2", ["file3", "file4", "file5"]),
                ]
            ),
        ),
        (
            # not list
            """
            repos: "string"
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:8: expected sequence of repos, got string."
            ),
        ),
        (
            # repeated file across repos
            """
            repos:
              - source: source1
                files: [file1, file2, file3]
              - source: source2
                files: [file5, file4, file3]
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:5:27: duplicate file 'file3'; already used on line 3."
            ),
        ),
        (
            # repeated repos
            """
            repos:
              - source: sourceA
                files: [fromSourceA]
              - source: sourceB
                files: [fromSourceB]
              - source: sourceA
                files: [fromSourceAAgain]
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:6:13: duplicate source 'sourceA'; already used on line 2."
            ),
        ),
        (
            # missing key
            """
            {}
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:1: mirror mapping is missing the key 'repos'."
            ),
        ),
        (
            # type
            """
            respo: []
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:1: invalid key 'respo', did you mean 'repos'?"
            ),
        ),
        (
            # extra key
            """
            repos: [{source: source, files: [file]}]
            extra_key: ":wave:"
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:2:1: mapping key should be one of ['repos'], got 'extra_key'."
            ),
        ),
        (
            # cyclic reference
            """
            repos: &R
              - source: source
                files: *R
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:8: recursive reference detected."
            ),
        ),
        (
            # wrong type
            """
            []
            """,
            snapshot(
                "An unexpected error occurred during parsing @ <string>:1:1: expected mirror mapping, got sequence."
            ),
        ),
    ],
)
def test_parse_mirror_config(yaml_node: Node, expected: MirrorConfig | str) -> None:
    _test_parse_body(yaml_node, expected, method_name="parse_mirror_config")


@pytest.mark.parametrize(
    "filename, expected",
    [
        (
            "config_tests/single.yaml",
            quick_mirror_config(
                [
                    quick_mirror_repo_config(
                        "https://github.com/George-Ogden/dbg", ["pyproject.toml"]
                    )
                ]
            ),
        ),
        (
            "config_tests/multiple.yaml",
            quick_mirror_config(
                [
                    quick_mirror_repo_config(
                        "https://github.com/George-Ogden/mypy-pytest",
                        ["pyproject.toml", ("requirements-dev.txt", "requirements.txt")],
                    ),
                    quick_mirror_repo_config(
                        "git@github.com:George-Ogden/actions.git",
                        [
                            (
                                ".github/workflows/python-release.yaml",
                                ".github/workflows/release.yaml",
                            ),
                            (
                                ".github/workflows/python-test.yaml",
                                ".github/workflows/test.yaml",
                            ),
                            (
                                ".github/workflows/lint.yaml",
                                ".github/workflows/lint.yaml",
                            ),
                        ],
                    ),
                ]
            ),
        ),
        (
            "config_tests/content_error.yaml",
            snapshot(
                "An unexpected error occurred during parsing @ TEST_DATA/config_tests/content_error.yaml:7:9: duplicate file 'mirror.yaml'; already used on line 4."
            ),
        ),
        (
            "config_tests/execution.yaml",
            snapshot(
                "An unexpected error occurred during parsing @ TEST_DATA/config_tests/execution.yaml:2:1: mapping key should be one of ['repos'], got 'args'."
            ),
        ),
        (
            "config_tests/syntax_error.yaml",
            snapshot(
                'while scanning a simple key in "TEST_DATA/config_tests/syntax_error.yaml", line 4, column 1 could not find expected \':\' in "TEST_DATA/config_tests/syntax_error.yaml", line 5, column 1'
            ),
        ),
        (
            "config_tests/doesnotexist.yaml",
            snapshot(
                "[Errno 2] No such file or directory: 'TEST_DATA/config_tests/doesnotexist.yaml'"
            ),
        ),
    ],
)
def test_parse_files(
    filename: str, expected: MirrorConfig | Exception | str, test_data_path: AbsDir
) -> None:
    filepath = test_data_path / RelFile(filename)
    if isinstance(expected, str | UndecidedValue | Exception):
        with pytest.raises((YAMLError, OSError)) as e:
            Parser.parse_file(filepath)
        error_msg = str(e.value)
        file_normalized_msg = error_msg.replace(str(test_data_path.path), "TEST_DATA")
        space_normalized_msg = " ".join(
            line.strip() for line in file_normalized_msg.splitlines() if line.strip()
        )
        assert space_normalized_msg == expected
    else:
        assert Parser.parse_file(filepath) == expected
