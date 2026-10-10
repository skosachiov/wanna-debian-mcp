# Proposal

## Why

The project ships a `wanna-debian-mcp` HTTP MCP server and a `Dockerfile`, but
the only documented container path uses Docker and has not been verified to
actually build and serve the MCP endpoint. Users on daemonless/rootless
container setups (podman) — including ones that need a privileged container for
mounts and build/metadata work — have no tested path to install from git, build
the image, run it, and confirm the server answers MCP requests.

## What Changes

- Add a documented **podman workflow** for the MCP server: install from git with
  `pip install --user --break-system-packages git+https://github.com/skosachiov/wanna-debian.git`,
  build the image with `podman build`, and run it with
  `podman run --privileged` (the same image, privileged so operations that need
  mounts/build tooling can work).
- Document how to **verify the MCP server** in the container: the endpoint
  (`http://<host>:8000/mcp`) answers an initialize/list-tools request and a
  representative tool call.
- Add **verification** that the image builds under podman and the containerized
  server serves the MCP endpoint, so the documented commands stay true.
- Align the existing Docker-based container docs with the podman workflow,
  including the no-authentication exposure warning.
- No behavior changes to MCP tools, the server, or packaging; the `Dockerfile`
  runtime contract is unchanged.

## Capabilities

### New Capabilities

- None. This change documents and verifies an existing container workflow; it
  does not introduce new system behavior.

### Modified Capabilities

- None. The container behavior these docs describe is already defined by the
  in-flight `mcp-server` capability. This change adds no new requirement deltas,
  so `.openspec.yaml` sets `skip_specs: true`.

## Impact

- **Docs**: `README.md` and `docs/mcp/index.md` gain a podman install/build/run
  and verification section; existing Docker commands are cross-referenced.
- **Tests**: a container smoke test under `tests/mcp/` that builds with podman
  (or Docker as a fallback) and checks the MCP endpoint, skipped when no
  container runtime is available and marked `integration`.
- **No product code changes**: no changes to `wanna_debian_mcp/`, `pyproject.toml`
  entry points, dependencies, or the `Dockerfile`. `pip install` without the
  `mcp` extra is unaffected.
