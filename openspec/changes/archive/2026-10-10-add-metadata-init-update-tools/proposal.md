# Proposal

## Why

The MCP server can pull Debian metadata, but only through a single
`update_metadata` tool that requires `base_url` on every call and never reads
back the `config.json` it writes. The `distrotracker` CLI supports two distinct
modes — initializing a named workspace with `-B <url>`
(`distrotracker -u -D debian -B http://ftp.debian.org/debian/`) and later
refreshing it from the stored URL (`distrotracker -u -D debian`) — and MCP
clients have no way to express either cleanly. Agents must remember and re-pass
the repository URL, and there is no explicit "create this workspace" step.

## What Changes

- Add an `init_metadata` MCP tool that initializes a named metadata workspace:
  it persists the workspace config (base URL, components, builds, architecture,
  TLS setting) and performs the initial pull. Mirrors
  `distrotracker -u -D debian -B http://ftp.debian.org/debian/`.
- Rework the existing `update_metadata` tool so `base_url` is optional; when
  omitted it reads the workspace's stored config and refreshes from the stored
  base URL. Mirrors `distrotracker -u -D debian`.
- **BREAKING (tool schema)**: `update_metadata.base_url` changes from required
  to optional, and the omitted-argument behavior (use the stored workspace
  config) is new.
- Identify workspaces by a name resolved under the server metadata root
  (`--metadata-dir` / `$WANNA_DEBIAN_METADATA_DIR` / `./metadata`), so
  `workspace="debian"` maps to `<root>/debian`.
- Persist and reuse the workspace config across calls, and report a clear,
  actionable error when `update_metadata` targets an uninitialized workspace
  without a base URL.
- Update the MCP documentation and add tests for initialization, stored-config
  updates, and the "base URL differs from the stored config" guard.

Out of scope: changing the repository fetch logic (`update_metadata` internals),
the search/analysis tools, or the `distrotracker` CLI.

## Capabilities

### New Capabilities

- `distro-metadata`: extends the metadata tracking behavior with named-workspace
  initialization and stored-config updates. `openspec/specs/` is currently empty
  because the `add-debian-mcp-server` change that introduces this capability is
  still in flight, so the delta is expressed as ADDED requirements (see Impact
  for the coordination note).

### Modified Capabilities

- None. There are no specs under `openspec/specs/` yet, so this change
  contributes an ADDED delta to the `distro-metadata` capability rather than a
  MODIFIED one.

## Impact

- **Code**: `wanna_debian_mcp/tools.py` gains `init_metadata` and a reworked
  `update_metadata` (optional `base_url`, stored-config read-back);
  `wanna_debian_mcp/server.py` registers `init_metadata` and updates the
  `update_metadata` signature.
- **Docs**: `docs/mcp/index.md` and `README.md` document the two tools and the
  workspace model.
- **Tests**: `tests/mcp/test_tools.py` unit tests for init/update/stored-config
  and the base-URL-mismatch guard; the update integration test is updated for
  the new flow.
- **Coordination**: `distro-metadata` is also added by the in-flight
  `add-debian-mcp-server` change. With an empty `openspec/specs/`, both changes
  carry ADDED deltas, so archive order matters — this change should be archived
  after (or its requirements merged into) `add-debian-mcp-server` to avoid a
  duplicate/conflicting `distro-metadata` spec.
- **Compatibility**: existing callers that pass `base_url` positionally to
  `update_metadata` keep working; only the tool schema relaxes a required field.
