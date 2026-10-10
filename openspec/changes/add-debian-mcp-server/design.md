# Design

## Context

See `proposal.md - Why`. The relevant current state:

- Existing packages `distrotracker`, `predose` expose logic as CLI entry points.
  `distrotracker.main()` mutates a module-global `config` dict and reads from
  stdin; `find_versions()` prints JSON to stdout. `predose.Metadata` already
  offers reusable methods (`resolve_src`, `resolve_bin`, `resolve_group`,
  `depends`, `rdepends`, `toposort`) that return strings.
- `distrotracker` depends on `apt_pkg` (system `python3-apt`) for version
  comparison, and some operations shell out to `dose-*`/`grep-dctrl`.
- `pyproject.toml` declares `requires-python = ">=3.8"` and a flat package
  layout (`predose`, `distrotracker`, `toposort`, `simplebuilder`).
- FastMCP is not yet a dependency; current FastMCP requires Python >= 3.10.

## Goals / Non-Goals

**Goals:**

- A discoverable MCP tool surface over the existing analysis/build-helper logic.
- No authentication, HTTP transport, loopback by default.
- Reuse existing functions; avoid duplicating version/dependency logic.
- A container image that runs the server with `apt_pkg` available.

**Non-Goals:**

- Auth/TLS/multi-tenant hosting, or any non-loopback security guarantee.
- Exposing `simplebuilder` sbuild/gbp back-ends.
- Rewriting `distrotracker`/`predose` internals or their CLI behavior.
- Persisting/backporting metadata mutations beyond what a tool call performs.

## Decisions

### Server package and entry point
Add a new flat package `wanna_debian_mcp/` with `server.py` (FastMCP app,
transport/config) and `tools.py` (tool functions). Register a console script
`wanna-debian-mcp = "wanna_debian_mcp.server:main"`. This matches the project's
flat layout and keeps wrappers out of the existing modules.

*Alternatives:* put the server in `distrotracker/` (mixes concerns); a
top-level `mcp_server/` name (less descriptive).

### FastMCP as an optional extra, lazy import
Add `fastmcp` under `[project.optional-dependencies] mcp` rather than core
`dependencies`, because FastMCP requires Python >= 3.10 while the project
declares `>=3.8`. `wanna-debian-mcp` imports FastMCP and, if missing, prints an
actionable message telling the user to install `wanna-debian[mcp]`.

*Alternatives:* core dependency (raises the effective Python floor for all
users); a separate distribution (extra packaging overhead).

### One tool per operation, grouped options
Expose a small set of tools rather than one per CLI flag:

- distro-metadata: `list_distributions`, `update_metadata`,
  `search_packages` (requirement list + dist/comp/build/arch filters, by-source,
  latest/earliest, brief, grep).
- dependency-analysis: `resolve_source`, `resolve_binaries`, `resolve_group`,
  `dependencies`, `reverse_dependencies`, `toposort`.

Each tool returns structured data (lists/dicts), not printed text.

*Alternatives:* mirror every CLI flag as its own tool (noisy, poor discovery);
a single "run distrotracker" tool (untyped, defeats MCP schema discovery).

### Reuse strategy
Call existing functions directly for pure logic (`parse_requirement_line`,
`check_version`, `Metadata` methods). For `find_versions`, extract its body into
an additive `collect_versions(...) -> list[dict]` that returns records; keep
`find_versions` printing exactly as before so existing tests/CLI are unchanged.
For `update_metadata`, set the fields on the `distrotracker.distrotracker.config`
module global (its existing contract) around the call instead of refactoring it.

*Alternatives:* capture stdout with `redirect_stdout` (fragile for large
results); subprocess the CLIs (loses structured output, slower, harder to test).

### Metadata location and config
Introduce a server workspace (default from `--metadata-dir` /
`WANNA_DEBIAN_METADATA_DIR`, falling back to `./metadata`; container uses
`/data/metadata`). Tools accept an optional metadata directory and fall back to
the configured default.

### HTTP binding
Default `--host 127.0.0.1 --port 8000`. The Dockerfile runs with
`--host 0.0.0.0` and `EXPOSE 8000` so the port is reachable from the host. No
auth by design; documentation will warn against public exposure.

### Concurrency safety
`apt_pkg.init()` is called once at startup. A process-wide `threading.Lock`
serializes metadata updates and any code touching the `config` global, since
that global is not thread-safe under concurrent HTTP requests.

### Container
Single-stage `debian:13` image. Install `python3`, `python3-pip`,
`python3-apt`, `python3-requests`, `python3-debian`, `dctrl-tools` (grep-dctrl),
`jq`, then `pip install --break-system-packages '.[mcp]'`. Use the **system**
interpreter (not a venv) so `python3-apt`'s `apt_pkg` is importable. `CMD`
runs `wanna-debian-mcp --host 0.0.0.0 --port 8000`.

*Alternatives:* multi-stage/venv (`apt_pkg` not on the venv path without
`--system-site-packages`); `python:3.x` base (must still apt-install
`python3-apt`).

## Risks / Trade-offs

- [No authentication] Anyone who can reach the port can run tools and trigger
  downloads/writes → bind loopback by default; document the risk; containers
  should publish only to trusted interfaces.
- [fastmcp/Python compatibility] fastmcp needs >= 3.10 but the project claims
  >= 3.8 → optional extra + explicit runtime guard; core library stays 3.8+.
- [`config` global mutation] `update_metadata` relies on module state, unsafe
  under concurrency → serialize with a lock; keep tool calls small.
- [Heavy/remote operations] `update_metadata` and some dependency tools can be
  slow or need network/`dose-*` → return progress-friendly errors, keep timeouts
  at the client, and mark such tests as integration.
- [stdout-based helper] `find_versions` couples logic to printing → additive
  `collect_versions` refactor keeps both paths working.

## Migration Plan

Additive change: new package, entry point, optional dependency, Dockerfile,
docs, and tests. No data or CLI migration; rollback is deleting the new package,
extra, script, and image. `pip install wanna-debian` without the `mcp` extra is
unaffected.

## Open Questions

- Exact default metadata directory (`./metadata` vs `~/.cache/wanna-debian`)
  can be finalized during implementation without changing the specs.
- Whether to package the server image under a registry tag/publish step is
  deferred; the Dockerfile itself is in scope.
