# Design

## Context

See `proposal.md - Why`. Relevant current state:

- `Dockerfile` builds a Debian-based image: installs system `python3` +
  `python3-apt`/`requests`/`debian`, `dctrl-tools`, `jq`, then
  `pip install --break-system-packages '.[mcp]'` into the system interpreter,
  sets `WANNA_DEBIAN_METADATA_DIR=/data/metadata`, `EXPOSE 8000`, and
  `CMD ["wanna-debian-mcp", "--host", "0.0.0.0", "--port", "8000", ...]`.
- `docs/mcp/index.md` documents only `docker build` / `docker run`.
- `tests/mcp/` covers the server in-process (`test_server.py`, `test_http.py`,
  `test_docs.py`) but has no image build/run test. `pyproject.toml` defines an
  `integration` marker.
- `docs/simplebuilder/index.md` already uses a `podman run -it --privileged ...`
  pattern for build environments, so podman is an established runtime here.
- `README.md` already documents the `pip install --user --break-system-packages
  git+https://...` path, but not a container build/run or MCP check.

## Goals / Non-Goals

**Goals:**

- A single copy-paste podman path: install from git → `podman build` →
  `podman run --privileged` → verify the MCP endpoint.
- Automated verification that keeps the documented commands honest: the image
  builds and the containerized server answers MCP requests.
- Keep the existing Docker instructions valid; document podman as an equivalent
  runtime rather than replacing Docker.

**Non-Goals:**

- Changing the MCP server, its tools, `pyproject.toml`, or the `Dockerfile`
  runtime contract.
- Adding sbuild/schroot back-ends or otherwise changing image contents.
- Registry publishing or CI pipeline changes.
- Guaranteeing rootless podman behavior when `--privileged` is not used.

## Decisions

### Document podman as a first-class runtime alongside Docker
Add a podman build/run/verify section, keeping the Docker examples and
cross-referencing them. Both runtimes are valid and users on daemonless setups
need podman to be explicit.

*Alternatives:* replace Docker (breaks existing users); a one-line podman note
(does not satisfy "check podman build").

### Document `podman run --privileged` for build/metadata work
Show the run command with `--privileged`, matching the request and the existing
`simplebuilder` pattern, and explain why: operations that touch mounts and build
tooling (and metadata writes) need elevated capabilities. Note the flag can be
dropped for pure read-only analysis calls.

*Alternatives:* always privileged without explanation (unclear, unsafe to
assume); never privileged (build/metadata operations fail).

### Verification via a `podman build` smoke test gated on runtime availability
Add `tests/mcp/test_container.py`, marked `integration`, that:
1. selects a runtime with `shutil.which("podman")` then `"docker"`, skipping
   with an actionable message when neither exists;
2. builds the image from the repo `Dockerfile`;
3. runs the container detached with a random published host port and a temporary
   metadata directory mounted at `/data/metadata`;
4. polls `http://127.0.0.1:<port>/mcp` until the server answers, then requests
   `initialize` + `tools/list` and asserts the expected tools are present;
5. tears the container down.

This exercises the same commands the docs show without breaking environments
that have no container runtime, and keeps the heavy step out of the default
suite.

*Alternatives:* an always-on test (fails where no runtime exists); manual-only
verification (drifts from the docs).

### Readiness by polling, not fixed sleeps
Poll the MCP endpoint with a bounded timeout instead of `sleep`, and use a random
host port to avoid collisions, so the test is robust and self-describing on
failure.

*Alternatives:* fixed sleep (flaky); fixed port 8000 (collides with a running
server).

## Risks / Trade-offs

- [Image build is slow and needs network/apt access] → mark the test
  `integration`, allow it to be skipped, and keep it out of the default fast run.
- [No podman/docker available in a dev or CI environment] → detect and `skip`
  with a clear message rather than failing.
- [`--privileged` is broad] → document that it exists for build/metadata
  operations, and keep the existing no-auth exposure warning.
- [Docs drift from the image] → the smoke test runs the documented commands, and
  `tests/mcp/test_docs.py` already ties docs to the registered tool schemas.

## Migration Plan

Additive: new doc sections plus one integration test. Rollback is deleting the
added doc text and the test file. No runtime, API, dependency, or packaging
changes.

## Open Questions

- Whether to wire `podman build` into CI is deferred; not required by this
  change.
