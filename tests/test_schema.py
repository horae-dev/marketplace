from __future__ import annotations

import copy
import json
from typing import Any

import pytest

from horae_marketplace.verify import (
    DEFAULT_INDEX,
    DEFAULT_SCHEMA,
    duplicate_names,
    load_json,
    schema_errors,
)

SHA = "a" * 40
VALID: dict[str, Any] = {
    "plugins": [
        {
            "name": "github",
            "repo": "https://github.com/horae-dev/plugin-github",
            "versions": {"0.1.0": SHA, "0.2.0-rc.1": "b" * 40},
            "tier": "first-party",
        }
    ]
}
SCHEMA = load_json(DEFAULT_SCHEMA)


def errors(index: Any) -> list[str]:
    return schema_errors(index, SCHEMA)


def test_committed_index_is_valid() -> None:
    assert errors(load_json(DEFAULT_INDEX)) == []
    assert duplicate_names(load_json(DEFAULT_INDEX)) == []


def test_valid_example() -> None:
    assert errors(VALID) == []


def mutate(path: tuple[Any, ...], value: Any) -> dict[str, Any]:
    doc = copy.deepcopy(VALID)
    target: Any = doc
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return doc


@pytest.mark.parametrize(
    "doc",
    [
        mutate(("extra",), 1),
        mutate(("plugins", 0, "extra"), 1),
        mutate(("plugins", 0, "name"), "GitHub"),
        mutate(("plugins", 0, "name"), "1plugin"),
        mutate(("plugins", 0, "repo"), "http://github.com/horae-dev/plugin-github"),
        mutate(("plugins", 0, "repo"), "git@github.com:horae-dev/plugin-github.git"),
        mutate(("plugins", 0, "repo"), "https://localhost/x/y"),
        mutate(("plugins", 0, "repo"), "https://github.com/../x"),
        mutate(("plugins", 0, "repo"), "https://user@github.com/a/b"),
        mutate(("plugins", 0, "tier"), "official"),
        mutate(("plugins", 0, "versions"), {}),
        mutate(("plugins", 0, "versions"), {"v0.1.0": SHA}),
        mutate(("plugins", 0, "versions"), {"0.1": SHA}),
        mutate(("plugins", 0, "versions"), {"0.1.0": "abc1234"}),
        mutate(("plugins", 0, "versions"), {"0.1.0": "A" * 40}),
        mutate(("plugins", 0, "versions"), {"0.1.0": "a" * 64}),
        mutate(("plugins", 0, "versions"), {"0.1.0": "main"}),
        {"plugins": {}},
        {},
    ],
)
def test_invalid_documents_are_rejected(doc: Any) -> None:
    assert errors(doc)


def test_duplicate_names_are_reported() -> None:
    doc = copy.deepcopy(VALID)
    doc["plugins"].append(copy.deepcopy(doc["plugins"][0]))
    assert duplicate_names(doc) == ["duplicate plugin name 'github'"]


def test_schema_is_strict_everywhere() -> None:
    text = json.dumps(SCHEMA)
    assert text.count('"additionalProperties": false') == 3
