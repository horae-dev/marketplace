<p align="center"><img src="https://raw.githubusercontent.com/horae-dev/.github/main/brand/horae-logo-500.png" width="96" alt="Horae logo"></p>

# marketplace

Git-based plugin index for Horae (marketplace.json) with CI that verifies every pinned plugin.

> 🚧 **Planned.** Nothing to install yet. Follow progress on the [Horae roadmap project](https://github.com/orgs/horae-dev/projects/1).

## What this repository will hold

`marketplace.json`, the index Horae reads to install plugins by name. Every entry pins a plugin version to a **commit SHA**; CI clones each entry, checks the SHA and runs the plugin's tests against the latest core.

## Planned work

| Milestone | Epic |
|---|---|
| M4 Marketplace | **Marketplace index** — marketplace.json, its schema and CI that verifies every entry. |

Stories, estimates and acceptance criteria are in this repository's [issues](../../issues) and on the [roadmap project](https://github.com/orgs/horae-dev/projects/1).

## Contributing

This project is developed mostly by AI coding agents supervised by a human maintainer. Read [AGENTS.md](AGENTS.md) for the workflow (it applies to humans too), and the organization's [contributing guide](https://github.com/horae-dev/.github/blob/main/CONTRIBUTING.md) and [security policy](https://github.com/horae-dev/.github/blob/main/SECURITY.md).

## License

[Apache-2.0](LICENSE)
