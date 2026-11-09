Closes #

## New plugin or new version

- Plugin name and version(s):
- Repository:
- Tier: `community` (a `first-party` entry is for the horae-dev organization only)
- Declared permissions (network hosts, secrets, paths, intents) and why each is needed:

## Checklist

See [CONTRIBUTING.md](../CONTRIBUTING.md). CI checks the first block; a reviewer checks the rest by hand.

- [ ] The repository was made from [horae-dev/template-plugin](https://github.com/horae-dev/template-plugin) (or follows its layout)
- [ ] Tag `v<version>` is on the exact commit, and the entry's SHA is its full 40-hex commit
- [ ] `plugin.yaml` at that commit declares the same name and version as the entry
- [ ] An existing version is not repointed to another SHA (a new version is a new entry)
- [ ] `uv run --with "git+https://github.com/horae-dev/horae@main" python -m horae_marketplace.verify` passes locally
- [ ] Declared permissions are minimal and match the code: every network host, secret, path and intent used is declared, and nothing else
- [ ] Tests exist and pass against core `main`
- [ ] The repository has an OSI-approved licence
- [ ] No install-time code execution is relied on: no submodules, no symlinks pointing out of the repository, no LFS
- [ ] The README documents the permissions
- [ ] The repository is not archived
- [ ] Private vulnerability reporting is enabled on the repository (security contact)
- [ ] 2FA is enabled for the maintainers (recommended)
