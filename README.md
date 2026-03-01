# Mirror|rorriM

## Motivation

How many Git repos do you have?
I have over 100 (but most of them are stale).
Even in the last two weeks (when this was made), I'd edited over 10 different ones.
They also rely on multiple configuration files that I frequently update (see all the ones in the root of this repo).
How do I manage them all?
I mirror them from a centralized config repo (https://github.com/George-Ogden/config).

## What is Mirror|rorriM?

Mirror|rorriM is a tool for syncing files between git repos.
Assume you have a working repo and you're mirroring files from a source repo.
It works with all the files in the config, but I'll illustrate with a `pytest.ini`.
Consider you have this config after you install mirror:

```ini
[pytest]
version = 9.0
markers =
    slow: affects the runtime of the test suite
```

Now you make the following changes:

<table>
<tr><th>Mirror Source</th><th>Working Repo</th></tr>
<tr><td>

```ini
[pytest]
version = 9.1
markers =
    slow: affects the runtime of the test suite
    local: skip on the remote test server
```

</td><td>

```ini
[pytest]
version = 9.0
markers =
    custom: only used in this repo
    slow: affects the runtime of the test suite
```

</td></tr>
</table>

When you run `mirror sync`, the changes (as a diff) are applied to your working version:

<table>
<tr><th>Remote Diff</th><th>Updated Working Repo</th></tr>
<tr><td>

```diff
 [pytest]
-version = 9.0
+version = 9.1
 markers =
 ...
     slow: affects the runtime of the test suite
+    local: skip on the remote test server
```

</td><td>

```ini
[pytest]
version = 9.1
markers =
    custom: only used in this repo
    slow: affects the runtime of the test suite
    local: skip on the remote test server
```

</td></tr>
</table>

**All changes are kept!** (You'll see a merge conflict if not.)

## Usage

Just follow these three steps:

0. Install from GitHub:

```bash
uv pip install git+https://github.com/George-Ogden/mirror-rorrim
```

(miss off the `uv` if you're still using `pip`).

1. Make a configuration file called `.mirror.yaml` in the root of your repository (skip this step if you already have a config you want to use):

```yaml
repos:
  - source: <location of config files> # anything you can git clone ...
    files:
      - mypy.ini # shorthand for mypy.ini: mypy.ini
      - pytest.ini: pytest.ini # format is target: source
      - ruff.toml

    # add more sources in the same format to sync from multiple repos
  - source: https://github.com/github/gitignore
    files:
      - .gitignore: Python.gitignore

  - source: https://github.com/licenses/license-templates
    files:
      - LICENSE: templates/mit.txt
```

_If you save this config, you can make it easy to setup your mirror again next time._

2. Install the mirror (make sure you've already run `git init`):

```bash
mirror install
```

For more advanced options, including using a remote config, see the help text:

```bash
mirror install --help
```

_After installing, it's a good idea to commit._

3. Periodically, sync your config files:

```bash
mirror sync
```

The updates in the repos you're syncing from are copied to your working repo.
_You can still edit your local files manually, but you may need to resolve conflicts when you sync._

### Pre-Commit

If you use, `pre-commit`, consider adding this repo as a hook to check for updates:

```yaml
- repo: https://github.com/George-Ogden/mirror-rorrim/
  rev: v0.4.6
  hooks:
    - id: mirror-check
```

## Contributing

Use GitHub for bugs/feature requests.
