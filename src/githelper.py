import git

from .typed_path import AbsDir, Remote


class GitHelper:
    @classmethod
    def clone(cls, remote: Remote, target: AbsDir) -> None:
        # Convert to string explicitly to gitpython-developers/GitPython#2085
        git.Repo.clone_from(remote.__fspath__(), target.__fspath__())
