# Tasks

## 1. Workspace resolution and `init_metadata`

- [x] 1.1 Add `get_workspace_dir(workspace=None, metadata_dir=None)` that treats `metadata_dir`/`$WANNA_DEBIAN_METADATA_DIR`/`./metadata` as the root, joins a workspace name under it, and uses an absolute `workspace` as-is. Verify unit tests cover the default root, a named workspace, the env root, and an absolute path.
- [x] 1.2 Implement `init_metadata(base_url, workspace=None, metadata_dir=None, dist=None, comp=None, build=None, sysarch="amd64", no_check_certificate=False, force=False)` that persists `config.json` (base URL, `ssl_verify`, `local_dir`, `sysarch`, `dist`, `comp`, `builds`, timestamp) and performs the initial pull. Verify a unit test (with `_update_metadata` monkeypatched) asserts the config file is written with the resolved directory and URL.
- [x] 1.3 Reject initialization without a base URL: raise a clear error and write no config. Verify a unit test asserts the error and that no `config.json` is created.
- [x] 1.4 Document `init_metadata` (arguments and an example such as `init_metadata(base_url="http://ftp.debian.org/debian/", workspace="debian")`) in `docs/mcp/index.md`. Verify the documented tool name and parameters match the schema checked by `tests/mcp/test_docs.py`.

## 2. `update_metadata` from stored configuration

- [x] 2.1 Read the workspace `config.json` in `update_metadata` when `base_url` is omitted and refresh from the stored URL; when no config exists and no URL is supplied, raise an actionable error naming `init_metadata`. Verify unit tests cover the reuse path and the uninitialized-workspace error.
- [x] 2.2 Persist a supplied base URL and reject a URL that differs from the stored one, leaving the stored configuration unchanged. Verify unit tests cover the config-less-with-URL case and the conflict rejection.
- [x] 2.3 Make `base_url` optional in the `update_metadata` signature/docstring while keeping existing calls working. Verify `tests/mcp/test_concurrency.py` and the positional-`base_url` usage still pass.
- [x] 2.4 Update the `update_metadata` documentation in `docs/mcp/index.md` for the optional base URL and stored-config behavior. Verify the docs mention `base_url` and the stored-config reuse.

## 3. Server surface and README

- [x] 3.1 Register `init_metadata` in `wanna_debian_mcp/server.py` and update the `update_metadata` tool signature. Verify an in-memory FastMCP client lists both `init_metadata` and `update_metadata`.
- [x] 3.2 Add `init_metadata` to the README tool list. Verify `tests/mcp/test_docs.py` passes (README lists every registered tool).

## 4. Integration verification

- [x] 4.1 Update `tests/mcp/test_integration.py` to initialize a workspace with `init_metadata`, then call `update_metadata` with no base URL and search the workspace. Verify `pytest -m integration` passes for the updated test.
- [x] 4.2 Run the fast suite (`pytest -m "not integration"`) and confirm there are no regressions.

## Workflow follow-up

- Archive the change after `add-debian-mcp-server` (or after merging the `distro-metadata` requirements) to keep the capability spec consistent.
