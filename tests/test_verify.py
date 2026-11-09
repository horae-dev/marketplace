from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from horae_marketplace.verify import Manifest, main, verify_entries

from .conftest import REPO_URL, fake_manifest

Cloner = Callable[[str, Path], None]


def index_for(versions: dict[str, str], name: str = "demo") -> dict[str, Any]:
    return {
        "plugins": [{"name": name, "repo": REPO_URL, "versions": versions, "tier": "first-party"}]
    }


def run(index: dict[str, Any], clone: Cloner) -> list[str]:
    return verify_entries(index, clone=clone, check_manifest=fake_manifest)


def test_correct_pin_passes(plugin_repo: dict[str, str], local_clone: Cloner) -> None:
    assert run(index_for({"0.1.0": plugin_repo["released"]}), local_clone) == []


def test_tampered_sha_fails(plugin_repo: dict[str, str], local_clone: Cloner) -> None:
    # A real commit of the repository, but not the one the tag points to.
    errors = run(index_for({"0.1.0": plugin_repo["later"]}), local_clone)
    assert len(errors) == 1
    assert "tag v0.1.0 points to" in errors[0]


def test_unknown_sha_fails(local_clone: Cloner) -> None:
    errors = run(index_for({"0.1.0": "f" * 40}), local_clone)
    assert len(errors) == 1
    assert "does not exist" in errors[0]


def test_missing_tag_fails(plugin_repo: dict[str, str], local_clone: Cloner) -> None:
    errors = run(index_for({"0.2.0": plugin_repo["later"]}), local_clone)
    assert errors
    assert "tag v0.2.0 does not exist" in errors[0]


def test_name_and_version_must_match_manifest(
    plugin_repo: dict[str, str], local_clone: Cloner
) -> None:
    errors = run(index_for({"0.1.0": plugin_repo["released"]}, name="other"), local_clone)
    assert errors
    assert "name is 'demo'" in errors[0]


def test_invalid_manifest_fails(plugin_repo: dict[str, str], local_clone: Cloner) -> None:
    def broken(_: Path) -> Manifest:
        from horae_marketplace.verify import VerifyError

        raise VerifyError("plugin.yaml is invalid: nope")

    errors = verify_entries(
        index_for({"0.1.0": plugin_repo["released"]}), clone=local_clone, check_manifest=broken
    )
    assert errors
    assert "plugin.yaml is invalid" in errors[0]


def write_index(tmp_path: Path, index: dict[str, Any]) -> Path:
    path = tmp_path / "marketplace.json"
    path.write_text(json.dumps(index))
    return path


def test_cli_exits_nonzero_on_tampered_sha(
    plugin_repo: dict[str, str],
    local_clone: Cloner,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    index = write_index(tmp_path, index_for({"0.1.0": plugin_repo["later"]}))
    code = main(["--index", str(index)], clone=local_clone, check_manifest=fake_manifest)
    assert code == 1
    assert "tag v0.1.0 points to" in capsys.readouterr().err


def test_cli_passes_on_correct_sha(
    plugin_repo: dict[str, str], local_clone: Cloner, tmp_path: Path
) -> None:
    index = write_index(tmp_path, index_for({"0.1.0": plugin_repo["released"]}))
    code = main(["--index", str(index)], clone=local_clone, check_manifest=fake_manifest)
    assert code == 0


def test_cli_rejects_schema_violation(tmp_path: Path) -> None:
    index = write_index(tmp_path, {"plugins": [{"name": "x"}]})
    assert main(["--index", str(index)]) == 1


def test_matrix_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    index = write_index(tmp_path, index_for({"0.1.0": "c" * 40}))
    assert main(["--index", str(index), "--matrix"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out == {
        "include": [{"name": "demo", "repo": REPO_URL, "version": "0.1.0", "sha": "c" * 40}]
    }


def test_semver_key_orders_releases_after_prereleases() -> None:
    from horae_marketplace.verify import semver_key

    versions = ["0.10.0", "0.3.1", "1.0.0-rc.1", "1.0.0", "0.3.0"]
    assert max(versions, key=semver_key) == "1.0.0"
    assert sorted(versions, key=semver_key)[:3] == ["0.3.0", "0.3.1", "0.10.0"]
