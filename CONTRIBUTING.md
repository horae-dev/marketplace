# Contributing a plugin to the marketplace

This repository is the default plugin index for [Horae](https://github.com/horae-dev/horae): one file, [`marketplace.json`](marketplace.json), that maps a plugin name to a git repository and to pinned commits. A plugin is listed by a pull request that adds an entry. This guide says how to submit one, what is checked, and what happens afterwards.

For the working rules of this repository itself (branches, commits, agents), see [AGENTS.md](AGENTS.md).

## 1. Submit a plugin

1. **Start from the template.** Use [`horae-dev/template-plugin`](https://github.com/horae-dev/template-plugin) ("Use this template" on GitHub). It has a `plugin.yaml`, an SDK-based server, recorded-input tests, CI and an [authoring checklist](https://github.com/horae-dev/template-plugin/blob/main/docs/authoring-checklist.md). Go through the checklist before you release.
2. **Release a version.** Set `version` in `plugin.yaml` (semver), commit, and tag that exact commit `v<version>` (for example `v0.1.0`). The tag name must be `v` followed by the version, and the `name` and `version` in `plugin.yaml` at that commit must match the index entry.
3. **Get the commit SHA.** `git rev-parse v<version>^{commit}` prints the full 40-hex SHA. Short SHAs and tag names are not accepted: the SHA is the pin.
4. **Add an entry** to `marketplace.json`, keeping the list sorted by name:

   ```json
   {
     "name": "acme",
     "repo": "https://github.com/you/plugin-acme",
     "versions": { "0.1.0": "<40-hex commit sha>" },
     "tier": "community"
   }
   ```

   - `name`: lowercase letters, digits and `-`, starting with a letter. It must be unique in the index.
   - `repo`: an `https://` git URL, with no port, credentials, query or fragment.
   - `versions`: each semver mapped to the commit that tag `v<version>` points to.
   - `tier`: `community` for anyone outside the horae-dev organization.
5. **Run the verifier locally.** It checks the schema, unique names, and, for every entry, clones the repository and checks the commit, the tag and `plugin.yaml`:

   ```
   uv run --with "git+https://github.com/horae-dev/horae@main" python -m horae_marketplace.verify
   ```

   Add `--schema-only` to check only the JSON while you edit.
6. **Open a pull request.** The template in `.github/PULL_REQUEST_TEMPLATE.md` is a checklist of everything below. Fill it in, and name the permissions your plugin declares and why.

## 2. What is checked

### By CI (every pull request)

- `marketplace.json` matches the [schema](schema/marketplace.schema.json): strict keys, name, semver, https repo URL, 40-hex commit.
- Names are unique.
- For every entry and version: the repository can be cloned over https, the pinned commit exists, tag `v<version>` points to that same commit, and `plugin.yaml` at that commit passes the core's validator (`horae` from git main) and declares the same name and version.

### By a reviewer, by hand

- **Permissions are minimal and match the code.** `plugin.yaml` declares every network host, secret (required and optional), readable and writable path, and intent type the plugin uses, and nothing more. The reviewer reads the code to confirm that each declaration is used and that nothing undeclared is.
- **Tests exist and pass** against the core's `main` (the SDK and `horae` from git main), not only against the versions in the plugin's lock file.
- **An OSI-approved licence** is in the repository, and `license` in `plugin.yaml` says which.
- **Nothing relies on install-time code execution.** The core installs a plugin by checking out the tree only, with hooks disabled, no submodules fetched, no LFS smudge, and symlinks that point outside the repository refused. A plugin that needs any of those cannot work, so do not use submodules, LFS, or symlinks that leave the repository.
- **The README documents the permissions**: what each host, secret, path and intent is for.
- **The repository is not archived** and is publicly reachable over https.
- **Maintainers should enable 2FA** on the account that owns the repository. This is recommended, not required.

The nightly workflow also runs each plugin's tests at its latest pinned version against core `main`, and opens or updates an issue when one fails. Older versions are not retested, since they are expected to drift from core.

## 3. Tiers

| Tier | Who | Review |
|---|---|---|
| `first-party` | Plugins maintained in the `horae-dev` organization | Reviewed by the core maintainers |
| `community` | Everyone else | Reviewed for the index rules above only. **Not audited.** |

A `community` listing is not an endorsement of the plugin's code. The user decides whether to trust a plugin: Horae is designed so that the user approves the declared permissions at install time. That approval step (#46) and the permission diff on upgrade (#47) are planned and not built yet; until they are, a plugin that is installed is not enabled automatically, and you should read its `plugin.yaml` before enabling it.

## 4. Update a plugin

A new version is a new entry under `versions`, in the same pull request format: release `v<new version>`, add `"<new version>": "<sha>"`, run the verifier, open a PR.

- **Never repoint an existing version to another SHA.** A version is immutable. A tag that moved after it was listed makes the install refuse (the tag and the pinned commit must be the same), and the verifier fails on it. If you released a bad version, publish a new one.
- Do not delete or force-move the `v<version>` tags of listed versions.
- If a new version adds a host, secret, path or intent, say so in the pull request. The reviewer treats it like a new submission for the permissions check.

## 5. Removal and security issues

- **Security issues.** If a listed version is found to be unsafe (malicious, leaking secrets, undeclared network access), the maintainers remove that version's entry from `versions`, or the whole plugin if no safe version remains. Removal is a pull request that explains why, and it takes priority over other reviews.
- **Report a problem** with a listed plugin through [GitHub private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability) on this repository. Do not open a public issue for a vulnerability.
- **Plugin authors** should turn on private vulnerability reporting on their own repository (Settings, Security) and name it in the README, so users know where to write to you.
- **Yanking.** To withdraw a version yourself (for example after a bug), open a pull request that removes it from `versions`, or ask in an issue. The next version number must be new: do not reuse a removed one.
- The maintainers may also remove a plugin whose repository is archived, deleted, or unmaintained and failing the nightly run for a long time, or whose tag no longer matches its pin.

## 6. Run your own index

You do not need this repository. Any https git repository that has a `marketplace.json` at its root in the same format works as an index. You can copy this repository's [schema](schema/marketplace.schema.json) and verifier for your own CI.

In `horae.yaml`, list the indexes in priority order, highest first (the default is this repository):

```yaml
marketplaces:
  - https://github.com/you/your-marketplace
  - https://github.com/horae-dev/marketplace
marketplace_pins:
  acme: https://github.com/you/your-marketplace
```

If the same plugin name is listed by several indexes under different repositories, Horae reports a conflict instead of choosing one. `marketplace_pins` maps a plugin name to the index it must come from. An index is untrusted data: it can only point to a repository and a commit, and the core re-checks the tag and the SHA at install.
