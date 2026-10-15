# Tasks

## 1. Isolate each workspace's persisted configuration

- [x] 1.1 In `wanna_debian_mcp/tools.py`, snapshot the distrotracker filter defaults at import (`_DEFAULT_DIST`, `_DEFAULT_COMP`, `_DEFAULT_BUILDS`, `_DEFAULT_SYSARCH`) from `_dt.config`; verify with a unit test that mutates `_dt.config` and asserts the snapshot still holds the original values.
- [x] 1.2 In `_pull_into_workspace`, assign `dist`, `comp`, `builds` and `sysarch` unconditionally on the global from the explicit argument or the snapshot (never leaving a prior workspace's value); verify with a test that initializes workspace A with `dist=["trixie"]`, then workspace B without filters, and asserts B's `config.json` has `dist == []` and the default `comp`/`builds`, with no `trixie` or `non-free`.
- [x] 1.3 Confirm `update_metadata` resolves missing fields from the workspace's own stored `config.json` (falling back to the snapshot only when absent) and verify a stored workspace keeps its own base URL and filters across an update.

## 2. Regression coverage for non-Debian repositories

- [x] 2.1 Add a `tests/mcp/test_tools.py` case with a non-Debian workspace name (e.g. `ubuntu`, base URL `http://archive.ubuntu.com/ubuntu/`) initialized after a `debian` workspace, asserting its persisted config contains no Debian distribution/component names.
- [x] 2.2 Add a case asserting a second `init_metadata` for the same workspace still rejects a conflicting base URL, and that an `update_metadata` call reads only that workspace's stored config.
- [x] 2.3 Run `python -m pytest tests/mcp/test_tools.py` and confirm the new and existing tool tests pass.

## 3. Document the isolation contract

- [x] 3.1 Update `docs/mcp/index.md` to state that each workspace is tied to one base URL and stores its own independent `dist`/`comp`/`build` filters, and note that a workspace already holding leaked filters must be re-initialized; verify the documented behavior matches the implemented defaults.

## Workflow follow-up

- Run `openspec validate recheck-debian-repo-names --strict` and resolve any findings.
- Archive the change after review requirements are satisfied.
