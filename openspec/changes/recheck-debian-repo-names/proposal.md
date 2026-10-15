# Proposal

## Why

Initializing a metadata workspace for a repository whose distribution/component
names are not Debian's (for example an Ubuntu mirror with `noble` and `universe`)
silently produces no useful metadata when another workspace was created earlier
in the same server process. `_pull_into_workspace` mutates the shared
`distrotracker.config` module global and only overwrites the fields the caller
passes, so a new workspace inherits the previous workspace's `dist` / `comp` /
`builds` (for example `trixie`, `non-free`) and persists them into its own
`config.json`. The workspace then searches the target repository for Debian
names that do not exist there.

## What Changes

- Compute each workspace's effective filters (`dist`, `comp`, `build`, `sysarch`)
  independently of any other workspace, so a workspace never inherits another
  base URL's persisted values.
- Persist each workspace's configuration from its resolved per-workspace values
  instead of dumping the mutable module-global `config`, so stale fields never
  reach another workspace's `config.json`.
- Keep the existing tool defaults for a workspace that supplies no filters
  (`dist` = all distributions, plus the documented default components and
  builds). No repository-specific name knowledge is added.
- No change to the CLI/MCP surface; only the derived per-workspace values become
  deterministic and isolated.

## Capabilities

### New Capabilities
<!-- None: this changes existing metadata-workspace behavior. -->

### Modified Capabilities
- `distro-metadata`: workspace initialization and update must derive and persist
  each workspace's configuration independently, so a workspace created for one
  base URL cannot inherit another base URL's distribution/component/build
  filters. Add a requirement for per-workspace configuration isolation and make
  the initialization requirement explicit that omitted filters resolve to
  repository-independent defaults.

## Impact

- `wanna_debian_mcp/tools.py`: `_pull_into_workspace`, `init_metadata`,
  `update_metadata` (the code that sets and dumps the shared config).
- `distrotracker/distrotracker.py`: the module-global `config` default contract
  (used as the repository-independent baseline; may gain a small helper to
  snapshot defaults).
- Tests: `tests/mcp/test_tools.py` — add coverage proving a second workspace does
  not inherit the first workspace's dist/comp/build, including a non-Debian
  (Ubuntu-style) workspace name.
- Docs: `docs/mcp/index.md` — clarify that each workspace's stored filters are
  independent (if the current wording implies otherwise).
