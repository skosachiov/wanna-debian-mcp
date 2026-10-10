# Proposal

## Why

The `wanna-debian` toolkit already knows how to track Debian distributions and
resolve package dependencies (`distrotracker`, `pre-dose`), but every operation
is reached through a CLI that reads from stdin and prints ad-hoc JSON/text.
MCP-capable agents and editors cannot discover or call these capabilities, and
there is no packaged, self-contained way to run them on a machine without
installing the whole build tool-chain.

Providing a local MCP server turns the existing analysis code into discoverable
tools so an agent can search packages, resolve source/binary relationships, and
walk dependency graphs directly, and a Dockerfile makes that server runnable
anywhere without manual setup.

## What Changes

- Add a **local MCP server** (built on FastMCP) that exposes `wanna-debian`
  analysis and build helpers as MCP tools.
- Transport is **streamable HTTP with no authentication**, bound to localhost by
  default; host/port are configurable via flags/env. (Not stdio.)
- Expose **distrotracker** capabilities: update/track distribution metadata and
  search packages/sources by version constraints.
- Expose **pre-dose** capabilities: resolve source→binary and binary→source,
  resolve build groups, compute forward/reverse dependencies, and topologically
  sort a backport set.
- Add the `fastmcp` runtime dependency and a console-script entry point.
- Add a **Dockerfile** that builds an image capable of running the HTTP MCP
  server locally (`python3-apt` and `requests` present, image exposes the port).
- Add tests for the new MCP tool layer.

Out of scope: authentication, TLS, multi-user isolation, and exposing the
`simplebuilder` sbuild/gbp build back-ends as MCP tools (the user asked for
"analysis and build MCP ... base functions", confirmed as distrotracker and
pre-dose).

## Capabilities

### New Capabilities

- `mcp-server`: The local, no-auth HTTP MCP server surface itself — transport,
  binding/config, tool discovery, input validation, result/error shaping, and
  running it from a container.
- `distro-metadata`: Distribution metadata tracking and package/source search
  behavior (update metadata, list distributions, find versions matching
  constraints, resolve a binary name to its source).
- `dependency-analysis`: Dependency and relationship analysis behavior over
  parsed `Packages`/`Sources` metadata (resolve binary/source/group, forward and
  reverse dependencies, topological sort).

### Modified Capabilities

- None. The project has no existing specs (`openspec/specs/` is empty), so no
  requirement deltas are needed.

## Impact

- **New code**: an MCP server module/package wrapping existing analysis
  functions; a Dockerfile for the server.
- **Entry points**: a new console script (e.g. `wanna-debian-mcp`) in
  `pyproject.toml`.
- **Dependencies**: add `fastmcp` (requires Python ≥ 3.10; the server entry point
  only works on 3.10+). Existing system deps `python3-apt` and `requests` are
  reused; `apt_pkg` and the `grep-dctrl`/`dose-*` CLI tools are external
  prerequisites for some operations.
- **Reused modules**: `distrotracker` (`update_metadata`, `find_versions`,
  `parse_requirement_line`, `check_version`) and `predose` (`Metadata` methods
  `resolve_src`, `resolve_bin`, `resolve_group`, `depends`, `rdepends`,
  `toposort`). No behavior changes to those modules.
- **Docs**: README / docs gain a short section on running the MCP server and
  container.
