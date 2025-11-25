from pathlib import Path

from .constants import MIRROR_CACHE


def test_mirror_cache_path() -> None:
    assert MIRROR_CACHE.path == Path("~/.cache/mirror").expanduser()


def test_mirror_cache_exists_as_folder() -> None:
    assert MIRROR_CACHE.exists()
    assert MIRROR_CACHE.is_folder()
