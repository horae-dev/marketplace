<p align="center"><img src="https://raw.githubusercontent.com/horae-dev/.github/main/brand/horae-logo-500.png" width="96" alt="Horae logo"></p>

# marketplace

Git-based plugin index for Horae (marketplace.json) with CI that verifies every pinned plugin.

## The index

[`marketplace.json`](marketplace.json) is the file Horae reads to install plugins by name:

```json
{ "plugins": [ { "name": "github", "repo": "https://github.com/horae-dev/plugin-github",
                 "versions": { "0.2.0": "<40-hex commit sha>" }, "tier": "first-party" } ] }
```

- Schema: [`schema/marketplace.schema.json`](schema/marketplace.schema.json) (strict; the name, semver, https repo URL and commit patterns match the core's `horae.lock` contract).
- `versions` maps a semver to the full commit SHA that the tag `v<version>` points to. The SHA is the pin.
- `tier` is `first-party` (horae-dev) or `community`.
- Only plugins (repos with a `plugin.yaml`) are listed. Pipeline packs (`pack-*`) are not part of this index yet.
- An entry is added only for a released (tagged) version. Nothing is listed until its repo has a `v<version>` tag.

## Verification

`uv run marketplace-verify` checks the schema and unique names, then, for every entry and version, clones the repo (https only), checks that the pinned commit exists, that tag `v<version>` points to the same commit, and that `plugin.yaml` at that commit passes the core's validator and declares the same name and version. It needs `horae` installed (CI uses git main): `uv run --with "git+https://github.com/horae-dev/horae@main" marketplace-verify`. Use `--schema-only` to skip git.

- CI (`ci.yml`) runs lint, types, tests (including a tampered-SHA fixture) and the verification on every PR and push to main.
- The nightly workflow (`nightly.yml`) runs each plugin's tests at its pinned SHA against core main and opens or updates an issue when one fails.

## Contributing

This project is developed mostly by AI coding agents supervised by a human maintainer. Read [AGENTS.md](AGENTS.md) for the workflow (it applies to humans too), and the organization's [contributing guide](https://github.com/horae-dev/.github/blob/main/CONTRIBUTING.md) and [security policy](https://github.com/horae-dev/.github/blob/main/SECURITY.md).

## License

[Apache-2.0](LICENSE)
