import functools
import os
import shutil

import git

from .typed_path import AbsDir, Remote


class GitHelper:
    @classmethod
    @functools.cache
    def checkout(cls, remote: Remote, local: AbsDir) -> None:
        try:
            cls._clone(remote, local)
        except git.GitCommandError as e:
            try:
                try:
                    cls._sync(local)
                except git.InvalidGitRepositoryError:
                    shutil.rmtree(local, ignore_errors=True)
                    cls._clone(remote, local)
            except Exception:
                raise e from None

    @classmethod
    def _clone(cls, remote: Remote, local: AbsDir) -> None:
        # Convert to string explicitly to gitpython-developers/GitPython#2085
        git.Repo.clone_from(os.fspath(remote), os.fspath(local))

    @classmethod
    def _sync(cls, local: AbsDir) -> None:
        # gitpython-developers/GitPython#2085
        repo = git.Repo(os.fspath(local))
        [fetch_info] = repo.remote().fetch()
        repo.head.reset(fetch_info.commit, working_tree=True, index=True)

    @classmethod
    def commit(cls, local: AbsDir) -> str:
        # gitpython-developers/GitPython#2085
        repo = git.Repo(os.fspath(local))
        return repo.head.commit.hexsha
