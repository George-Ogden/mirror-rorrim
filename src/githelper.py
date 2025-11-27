import git

from .typed_path import AbsDir, Remote


class GitHelper:
    @classmethod
    def clone(cls, remote: Remote, local: AbsDir) -> None:
        # Convert to string explicitly to gitpython-developers/GitPython#2085
        git.Repo.clone_from(remote.__fspath__(), local.__fspath__())

    @classmethod
    def sync(cls, remote: Remote, local: AbsDir) -> None:
        # gitpython-developers/GitPython#2085
        repo = git.Repo(local.__fspath__())
        [fetch_info] = repo.remote().fetch()
        repo.head.reset(fetch_info.commit, working_tree=True, index=True)
