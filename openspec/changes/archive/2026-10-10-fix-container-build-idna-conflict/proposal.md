# Proposal

## Why

The container image no longer builds: `docker`/`podman build` fails at
`pip install --break-system-packages --no-cache-dir '.[mcp]'` with
`error: uninstall-no-record-file` because pip must upgrade the Debian
apt-installed `python3-idna` 3.10 (no `RECORD` file) to satisfy `httpx2>=2.5`,
which the `mcp` extra pulls in via `fastmcp`/`mcp` and which requires
`idna>=3.18`. This blocks the documented container path and the two in-flight
changes that verify it (`add-debian-mcp-server` task 5, `add-podman-mcp-workflow`
tasks 2.2-3.2).

## What Changes

- Fix the `Dockerfile` MCP-extra install so the build succeeds on the Debian
  base image despite its apt-managed Python packages: pass `--ignore-installed`
  to the existing `pip install --break-system-packages` command, so pip no
  longer tries to uninstall the distro's `python3-idna` (and any other
  externally-managed package) and instead installs the needed versions into
  `/usr/local`.
- Keep the image's existing runtime contract unchanged: system `python3`, so
  `apt_pkg` from `python3-apt` and the `debian` module from `python3-debian`
  stay importable; same `WANNA_DEBIAN_METADATA_DIR`, `EXPOSE 8000`, and
  `CMD`/entry point.
- Update the container notes in `README.md` / `docs/mcp/index.md` only if they
  need to mention the flag; the documented build/run commands stay the same.

## Capabilities

### New Capabilities

- None. This is a build/tooling fix that restores the existing Dockerfile
  behavior; it introduces no new system behavior.

### Modified Capabilities

- None. The `mcp-server` capability already requires that the image build and
  serve the HTTP MCP endpoint (`Container packaging`); this change makes the
  build actually satisfy that requirement rather than changing it. No
  requirement deltas are needed, so `.openspec.yaml` sets `skip_specs: true`.

## Impact

- **Build**: `Dockerfile` `RUN pip install ... '.[mcp]'` line only.
- **No product code changes**: no changes to `wanna_debian_mcp/`,
  `distrotracker/`, `predose/`, `pyproject.toml` entry points, or the dependency
  set. A bare `pip install` without the `mcp` extra is unaffected.
- **Unblocks**: `tests/mcp/test_container.py` (image build + MCP endpoint smoke
  test) and the container build/run tasks in `add-debian-mcp-server` and
  `add-podman-mcp-workflow`.
- **Risk**: `--ignore-installed` lets pip install dependencies that also exist
  as apt packages; because pip writes to `/usr/local` while apt's copies remain
  in `/usr/lib/python3/dist-packages`, `apt_pkg` stays importable and the two
  trees coexist.
