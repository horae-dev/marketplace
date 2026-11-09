"""Verify marketplace.json: schema, unique names, then every entry and version against git.

For each (plugin, version) the repository is cloned (https only), and the script checks that

* the pinned commit exists in the clone,
* the tag ``v<version>`` exists and points to that same commit (annotated tags are peeled),
* ``plugin.yaml`` at that commit is valid and declares the same name and version.

Any mismatch is an error and the exit code is 1. ``plugin.yaml`` is validated with the core's
own contract (``horae.contracts.plugin.PluginManifest``), so ``horae`` must be installed (CI
installs it from git main).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INDEX = ROOT / "marketplace.json"
DEFAULT_SCHEMA = ROOT / "schema" / "marketplace.schema.json"
TAG_PREFIX = "v"
GIT_TIMEOUT_S = 300


class VerifyError(Exception):
    """One entry or version failed verification."""


@dataclass(frozen=True)
class Manifest:
    name: str
    version: str


Cloner = Callable[[str, Path], None]
ManifestChecker = Callable[[Path], Manifest]


def _git(cwd: Path, *args: str, allow: str = "never") -> str:
    # Never inherit user/system git config; only the named protocol may be used.
    cmd = [
        "git",
        "-c",
        "protocol.allow=never",
        "-c",
        f"protocol.{allow}.allow=always",
        *args,
    ]
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "LANG", "TMPDIR"}}
    env.update(
        GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null", GIT_TERMINAL_PROMPT="0"
    )
    try:
        done = subprocess.run(  # noqa: S603
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise VerifyError(f"git {args[0]} timed out") from exc
    if done.returncode != 0:
        raise VerifyError(f"git {args[0]} failed: {done.stderr.strip()[:300]}")
    return done.stdout.strip()


def clone_https(url: str, dest: Path) -> None:
    """Clone `url` into `dest` over https only: all branches and tags, without file contents."""
    _git(
        dest.parent,
        "clone",
        "--quiet",
        "--no-checkout",
        "--filter=blob:none",
        "--",
        url,
        str(dest),
        allow="https",
    )
    _git(dest, "fetch", "--quiet", "--tags", "--force", "origin", allow="https")


def horae_manifest_checker(manifest_text: Path) -> Manifest:
    """Validate a plugin.yaml file with the core's contract."""
    try:
        from horae.config import ProblemsError, read_yaml, validate
        from horae.contracts.plugin import PluginManifest
    except ImportError as exc:  # pragma: no cover - environment problem
        raise VerifyError(
            "horae is not installed; install it from git main to validate plugin.yaml"
        ) from exc
    try:
        manifest = validate(read_yaml(manifest_text), PluginManifest)
    except ProblemsError as exc:
        raise VerifyError(
            "plugin.yaml is invalid: " + "; ".join(str(p) for p in exc.problems)
        ) from exc
    return Manifest(name=str(manifest.name), version=str(manifest.version))


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise VerifyError(f"{path}: cannot read as JSON: {exc}") from exc


def schema_errors(index: Any, schema: Any) -> list[str]:
    validator = Draft202012Validator(schema)
    return [
        f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in sorted(validator.iter_errors(index), key=lambda e: list(map(str, e.absolute_path)))
    ]


def duplicate_names(index: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    dupes: list[str] = []
    for entry in index["plugins"]:
        if entry["name"] in seen:
            dupes.append(f"duplicate plugin name {entry['name']!r}")
        seen.add(entry["name"])
    return dupes


def verify_version(
    clone_dir: Path,
    name: str,
    version: str,
    sha: str,
    check_manifest: ManifestChecker,
) -> None:
    """Check one pinned version inside an existing clone."""
    try:
        _git(clone_dir, "cat-file", "-e", f"{sha}^{{commit}}")
    except VerifyError as exc:
        raise VerifyError(f"pinned commit {sha} does not exist in the repository") from exc
    tag = f"{TAG_PREFIX}{version}"
    try:
        tag_sha = _git(clone_dir, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}")
    except VerifyError as exc:
        raise VerifyError(f"tag {tag} does not exist") from exc
    if tag_sha != sha:
        raise VerifyError(f"tag {tag} points to {tag_sha}, but the index pins {sha}")
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "plugin.yaml"
        try:
            content = _git(clone_dir, "show", f"{sha}:plugin.yaml")
        except VerifyError as exc:
            raise VerifyError(f"no plugin.yaml at {sha}") from exc
        target.write_text(content + "\n", encoding="utf-8")
        manifest = check_manifest(target)
    if manifest.name != name:
        raise VerifyError(f"plugin.yaml name is {manifest.name!r}, the index says {name!r}")
    if manifest.version != version:
        raise VerifyError(
            f"plugin.yaml version is {manifest.version!r}, the index says {version!r}"
        )


def verify_entries(
    index: dict[str, Any],
    *,
    clone: Cloner = clone_https,
    check_manifest: ManifestChecker = horae_manifest_checker,
) -> list[str]:
    """Verify every entry and version. Returns the list of errors (empty when all is well)."""
    errors: list[str] = []
    for entry in index["plugins"]:
        name, repo = entry["name"], entry["repo"]
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "repo"
            try:
                clone(repo, dest)
            except VerifyError as exc:
                errors.append(f"{name}: cannot clone {repo}: {exc}")
                continue
            for version, sha in entry["versions"].items():
                try:
                    verify_version(dest, name, version, sha, check_manifest)
                except VerifyError as exc:
                    errors.append(f"{name}@{version}: {exc}")
                else:
                    print(f"ok  {name}@{version} {sha}")
    return errors


def main(
    argv: Sequence[str] | None = None,
    *,
    clone: Cloner = clone_https,
    check_manifest: ManifestChecker = horae_manifest_checker,
) -> int:
    parser = argparse.ArgumentParser(description="Verify a Horae marketplace index.")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument(
        "--schema-only", action="store_true", help="validate the schema and names; skip git"
    )
    parser.add_argument(
        "--matrix",
        action="store_true",
        help="print the entries as a GitHub Actions matrix (JSON) and exit",
    )
    args = parser.parse_args(argv)
    try:
        index = load_json(args.index)
        schema = load_json(args.schema)
    except VerifyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    errors = schema_errors(index, schema)
    if not errors:
        errors = duplicate_names(index)
    if errors:
        for message in errors:
            print(f"error: {args.index}: {message}", file=sys.stderr)
        return 1
    if args.matrix:
        include = [
            {"name": e["name"], "repo": e["repo"], "version": v, "sha": sha}
            for e in index["plugins"]
            for v, sha in e["versions"].items()
        ]
        print(json.dumps({"include": include}))
        return 0
    print(f"schema ok: {len(index['plugins'])} plugin(s)")
    if args.schema_only:
        return 0
    errors = verify_entries(index, clone=clone, check_manifest=check_manifest)
    for message in errors:
        print(f"error: {message}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
