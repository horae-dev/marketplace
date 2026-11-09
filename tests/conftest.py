"""Fixtures: tiny local plugin repositories and an index that pins them."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from horae_marketplace.verify import Manifest, VerifyError

REPO_URL = "https://example.invalid/horae-dev/plugin-demo"


def git(cwd: Path, *args: str) -> str:
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
    }
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def plugin_repo(tmp_path: Path) -> dict[str, str]:
    """A repo with one commit tagged v0.1.0 (annotated) and a later untagged commit."""
    repo = tmp_path / "src-repo"
    repo.mkdir()
    git(repo, "init", "--quiet", "-b", "main")
    (repo / "plugin.yaml").write_text("name: demo\nversion: 0.1.0\n")
    git(repo, "add", ".")
    git(repo, "commit", "--quiet", "-m", "release")
    released = git(repo, "rev-parse", "HEAD")
    git(repo, "tag", "-a", "v0.1.0", "-m", "v0.1.0")
    (repo / "extra.txt").write_text("later\n")
    git(repo, "add", ".")
    git(repo, "commit", "--quiet", "-m", "later")
    return {"path": str(repo), "released": released, "later": git(repo, "rev-parse", "HEAD")}


@pytest.fixture
def local_clone(plugin_repo: dict[str, str]) -> Callable[[str, Path], None]:
    """A cloner that ignores the URL and clones the fixture repo from disk."""

    def clone(url: str, dest: Path) -> None:
        assert url == REPO_URL
        git(dest.parent, "clone", "--quiet", "--no-checkout", plugin_repo["path"], str(dest))

    return clone


def fake_manifest(path: Path) -> Manifest:
    data = dict(line.split(": ", 1) for line in path.read_text().splitlines() if ": " in line)
    if "name" not in data:
        raise VerifyError("plugin.yaml is invalid: name missing")
    return Manifest(name=data["name"], version=data["version"])
