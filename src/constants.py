from pathlib import Path

import platformdirs

from .typed_path import AbsDir, RelFile

MIRROR_LOCK: RelFile = RelFile(Path(".mirror.lock"))
MIRROR_FILE: RelFile = RelFile(Path(".mirror.yaml"))
MIRROR_CACHE: AbsDir = AbsDir(Path(platformdirs.user_cache_dir("mirror")))

MIRROR_CACHE.path.mkdir(parents=True, exist_ok=True)
