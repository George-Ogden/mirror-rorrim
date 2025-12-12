from collections.abc import Sequence

import pytest
from yaml import Node, YAMLError

from .state import AutoState, MirrorRepoState, MirrorState
from .typed_path import AbsDir, Commit, RelDir, RelFile, Remote


@pytest.fixture
def test_data_path(global_test_data_path: AbsDir) -> AbsDir:
    return global_test_data_path / RelDir("state_tests")


def quick_mirror_repo_state(source: str, commit: str, files: list[str]) -> MirrorRepoState:
    return MirrorRepoState(Remote(source), Commit(commit), [RelFile(file) for file in files])


def quick_mirror_state(mirror_repos: list[MirrorRepoState]) -> MirrorState:
    return MirrorState(mirror_repos)


@pytest.mark.parametrize(
    "cls, raw_yaml, expected",
    [
        # string
        (str, "string", "string"),
        # sequence instead of string
        (str, "[]", None),
        # single-field dataclass
        (Remote, "remote", Remote("remote")),
        # mapping instead of string
        (Remote, "remote: remote", None),
        # different single-field dataclass
        (Commit, "commit", Commit("commit")),
        (
            # sequence of strings
            Sequence[str],  # type: ignore[type-abstract]
            """
            - a
            - b
            - c
            """,
            ["a", "b", "c"],
        ),
        (
            # mapping instead of sequence
            Sequence[str],  # type: ignore[type-abstract]
            """
            a: b
            c: d
            """,
            None,
        ),
        (
            # sequence of sequences instead of sequence of strings
            Sequence[str],  # type: ignore[type-abstract]
            """
            - []
            - []
            """,
            None,
        ),
        (
            # sequence of single-field dataclasses
            Sequence[Commit],  # type: ignore[type-abstract]
            """
            - commit1
            - commit2
            - commit3
            """,
            [Commit("commit1"), Commit("commit2"), Commit("commit3")],
        ),
        (
            # many-field dataclass
            MirrorRepoState,
            """
            source: source
            commit: commit
            files: []
            """,
            quick_mirror_repo_state("source", "commit", []),
        ),
        (
            # many-field dataclass out of order
            MirrorRepoState,
            """
            files: [file]
            commit: commit
            source: source
            """,
            quick_mirror_repo_state("source", "commit", ["file"]),
        ),
        (
            # many-field dataclass missing fields
            MirrorRepoState,
            """
            source: source
            files: []
            """,
            None,
        ),
        (
            # many-field dataclass with extra field
            MirrorRepoState,
            """
            source: source
            commit: commit
            files: []
            unknown: 7
            """,
            None,
        ),
        (
            # many-field dataclass with sequence
            MirrorRepoState,
            """
            source: source
            commit: commit
            files:
                - file1
                - file2
                - file3
            """,
            quick_mirror_repo_state("source", "commit", ["file1", "file2", "file3"]),
        ),
        (
            # many-field dataclass as json
            MirrorRepoState,
            """
            {
                "files": ["file"],
                "commit": "commit",
                "source": "source",
            }
            """,
            quick_mirror_repo_state("source", "commit", ["file"]),
        ),
        (
            # sequence instead of many-field dataclass
            MirrorRepoState,
            """
            - source
            - commit
            - files: []
            """,
            None,
        ),
        (
            # full, empty state sequence
            MirrorState,
            """
            []
            """,
            quick_mirror_state([]),
        ),
        (
            # full, single-item state
            MirrorState,
            """
            - source: myremoterepo.org
              commit: abc
              files:
                - .gitignore
                - LICENSE
            """,
            quick_mirror_state(
                [quick_mirror_repo_state("myremoterepo.org", "abc", [".gitignore", "LICENSE"])]
            ),
        ),
        (
            # full, many-item state
            MirrorState,
            """
            - source: myremoterepo.org
              commit: abc
              files:
                - .gitignore
                - LICENSE
            - source: unused/folder/
              commit: def
              files: []
            """,
            quick_mirror_state(
                [
                    quick_mirror_repo_state("myremoterepo.org", "abc", [".gitignore", "LICENSE"]),
                    quick_mirror_repo_state("unused/folder/", "def", []),
                ]
            ),
        ),
        (
            # with comment
            MirrorState,
            """
            # Comment about editing at your own risk.
            - source: myremoterepo.org
              commit: abcdef
              files:
                - .mirror.yaml
            """,
            quick_mirror_state(
                [quick_mirror_repo_state("myremoterepo.org", "abcdef", [".mirror.yaml"])]
            ),
        ),
    ],
)
def test_construct_state[T](cls: type[T], yaml_node: Node, expected: T | None) -> None:
    if expected is None:
        with pytest.raises(YAMLError):
            AutoState.construct(cls, yaml_node)
    else:
        assert AutoState.construct(cls, yaml_node) == expected


@pytest.mark.parametrize(
    "filename, expected",
    [
        (
            "valid.yaml",
            quick_mirror_state(
                [
                    quick_mirror_repo_state(
                        "https://github.com/George-Ogden/mirror-config",
                        "fd0a098dfe0db14360741d3548db164c9b3d1004",
                        [
                            "python.gitignore",
                            "python.pre-commit-config.yaml",
                            "requirements-dev.txt",
                            "requirements.txt",
                        ],
                    )
                ]
            ),
        ),
        (
            "syntax_error.yaml",
            None,
        ),
        ("execution.yaml", None),
        ("missing_key.yaml", None),
    ],
)
def test_load(filename: str, expected: MirrorState | None, test_data_path: AbsDir) -> None:
    filepath = test_data_path / RelFile(filename)
    with open(filepath) as f:
        if expected is None:
            with pytest.raises(YAMLError):
                MirrorState.load(f)
        else:
            assert MirrorState.load(f) == expected
