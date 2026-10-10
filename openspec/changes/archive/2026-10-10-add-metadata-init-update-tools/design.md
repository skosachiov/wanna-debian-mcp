# Design

## Context

See `proposal.md - Why`. Relevant current state:

- `wanna_debian_mcp/tools.py` wraps distrotracker.
  `update_metadata(base_url, metadata_dir, dist, comp, build, sysarch,
  no_check_certificate, force)` requires `base_url`, sets fields on the
  `distrotracker.distrotracker.config` global, writes `<metadata_dir>/config.json`,
  and never reads it back.
- `distrotracker.main()` reads/writes `config.json` in its `-D` local dir: it
  requires `-B` when the config is missing and rejects a supplied base URL that
  differs from the stored one.
- `get_metadata_dir(metadata_dir)` resolves a directory from the argument, then
  `$WANNA_DEBIAN_METADATA_DIR`, then `./metadata` (currently the workspace
  itself, absolute).
- `server.py` registers flat tools; the search/analysis tools read a
  `metadata_dir`.
- Tests: `tests/mcp/test_tools.py` (unit), `test_concurrency.py` (serialization;
  calls `tools.update_metadata(base_url, metadata_dir=...)`), `test_integration.py`
  (real update then search), `test_docs.py` (docs ↔ tool schemas).

## Goals / Non-Goals

**Goals:**

- Two explicit operations: initialize a named workspace (base URL required) and
  update a workspace reusing its stored configuration.
- Workspace naming matches the CLI `-D` value, resolved under the server
  metadata root.
- Persist the configuration so updates do not need the URL, while keeping
  existing callers that pass `base_url`/`metadata_dir` working.

**Non-Goals:**

- Changing fetch internals, the `distrotracker` CLI, or the search/analysis
  tools.
- A workspace listing/inspection tool or a registry (not requested).
- New authentication/TLS behavior beyond the existing `no_check_certificate`.

## Decisions

### Two tools, and `update_metadata`'s `base_url` becomes optional
Add `init_metadata(base_url, workspace=None, ...)`: create/persist the workspace
config and pull. Rework `update_metadata(base_url=None, workspace=None, ...)`:
read the stored config and pull (using a supplied URL when given).

*Rationale:* mirrors the two CLI modes and keeps one refresh code path.
*Alternatives:* a separate `update_workspace` tool (extra surface, near-duplicate
of `update_metadata`); keep `base_url` required (does not satisfy the request).

### Workspace names resolve under a metadata root
Add `get_workspace_dir(workspace=None, metadata_dir=None)`:
`metadata_dir` (explicit), else `$WANNA_DEBIAN_METADATA_DIR`, else `./metadata`
is the **root**; a `workspace` name is joined under it, and an absolute
`workspace` is used as-is. With no `workspace`, the root is the workspace,
preserving today's `metadata_dir` meaning.

*Rationale:* `workspace="debian"` → `<root>/debian` mirrors `-D debian`, while
existing `metadata_dir=<path>` calls keep working.
*Alternatives:* treat `workspace` as a full path (does not match `-D`); maintain
a workspace registry (over-built).

### Persist and reuse a distrotracker-compatible `config.json`
Write `config.json` (base URL, `ssl_verify`, `local_dir`, `sysarch`, `dist`,
`comp`, `builds`, timestamp) into the workspace, and read it in
`update_metadata` when `base_url` is omitted.

*Rationale:* one source of truth shared with the CLI, using the file name the
CLI already uses.
*Alternatives:* an MCP-only config file (diverges from the CLI); no persistence
(the current limitation).

### Base-URL conflict semantics
On update, a supplied base URL that differs from the workspace's stored one is
rejected with an error (mirroring distrotracker's guard) instead of overwriting.
If nothing is stored, the supplied URL is persisted (backward compatible). If
nothing is supplied and nothing is stored, raise an actionable error naming
`init_metadata`.

*Rationale:* prevents silently repointing a workspace; matches CLI behavior.
*Alternatives:* always overwrite (surprising, data from two repos could mix);
ignore a supplied URL (ignores caller intent).

### Serialization
Reuse the existing process-wide `_LOCK` around config mutation and the fetch,
since `_dt.config` is a shared module global.

## Risks / Trade-offs

- [Tool schema change] `update_metadata.base_url` goes from required to
  optional → relaxing a required field is backward compatible for callers;
  document the schema change.
- [Root vs workspace ambiguity] `metadata_dir` historically was the workspace →
  keep it as the default workspace and only reinterpret it as a root when a
  `workspace` name is given; document both.
- [Config drift with the CLI] two writers of `config.json` → use the same file
  and keys and the same conflict guard.
- [Cross-change spec overlap] `distro-metadata` is introduced by the in-flight
  `add-debian-mcp-server` change → keep requirement names distinct and mind
  archive ordering (see proposal Impact).

## Migration Plan

Additive tool plus a relaxed signature. Existing `update_metadata(base_url, ...)`
calls continue to work. Rollback removes `init_metadata`, restores the required
argument, and drops config read-back.

## Open Questions

- Whether the search/analysis tools should also accept a `workspace` name is
  deferred; they keep `metadata_dir`, which already points at the workspace.
