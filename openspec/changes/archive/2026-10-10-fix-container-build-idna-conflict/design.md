# Design

## Context

See `proposal.md` - Why. Current state and constraints that shape the fix:

- `Dockerfile` installs the project and the `mcp` extra with
  `RUN pip install --break-system-packages --no-cache-dir '.[mcp]'` into the
  system interpreter. The image deliberately uses the Debian system `python3`
  so `apt_pkg` (`python3-apt`) and the `debian` module (`python3-debian`) stay
  importable to `distrotracker`/`predose`.
- The apt step installs `python3-requests`, which pulls `python3-idna` 3.10.
  Debian's apt-installed Python packages have no pip `RECORD`/`direct_url.json`,
  so pip cannot uninstall them.
- `fastmcp`/`mcp` (the `mcp` extra) depend on `httpx2`, which requires
  `idna>=3.18`. pip's resolver therefore schedules an `idna` install and, on
  finding 3.10 already present, tries to uninstall it and aborts with
  `uninstall-no-record-file`.
- The base image is `debian:13`; `requires-python >= 3.8` and the code paths we
  need are stdlib + apt, so the runtime stays on the distro interpreter.

## Goals / Non-Goals

**Goals:**

- Make `docker build` / `podman build` of the repo `Dockerfile` succeed
  unmodified on a clean `debian:13` base, with no manual steps.
- Preserve the image's runtime contract: system `python3`, `apt_pkg` and
  `debian` importable, `wanna-debian-mcp` on `PATH`, port 8000 exposed, same
  entry point and metadata dir.
- Keep the documented build/run commands unchanged.

**Non-Goals:**

- Changing MCP tools, the server, `pyproject.toml`, dependencies, or the set of
  apt packages installed.
- Pinning or downgrading `fastmcp`/`mcp`/`httpx2`.
- Solving Debian PEP 668 (externally-managed-environment) in general, or
  providing a fully isolated interpreter.

## Decisions

### Pass `--ignore-installed` to the existing system-python install

Change the one `RUN` line to
`pip install --break-system-packages --no-cache-dir --ignore-installed '.[mcp]'`.
`--ignore-installed` tells pip to disregard already-installed distributions, so
it stops trying to uninstall apt-managed packages and installs the full
dependency set into the pip-managed location (`/usr/local/lib/python3.x/...`),
which precedes `/usr/lib/python3/dist-packages` on `sys.path`. The newer `idna`
shadows the apt copy without touching it, and `apt_pkg`/`debian` remain
importable.

*Alternatives:*

- **Isolated virtualenv (`python3 -m venv --system-site-packages`)** - cleaner
  isolation in principle, but adds `python3-venv`, changes `PATH`/`CMD`, and a
  venv with system site-packages still exposes the apt `idna` to pip, so it can
  hit the same uninstall error; making it robust needs `--ignore-installed`
  anyway. Not worth the extra moving parts for a one-line fix.
- **Pin older `fastmcp`/`mcp`** - choose releases that depend on `httpx` rather
  than `httpx2` (whose `idna>=3.18` is the trigger). Rejected: freezes to older
  releases and will break again at the next dependency bump.
- **Drop `python3-requests`/`python3-idna` from the apt step** - would stop the
  conflict but changes the image's package contract and does not help once any
  apt package is externally managed.
- **`--break-system-packages` alone / manual `idna` pin in `pyproject.toml`** -
  does not prevent pip from attempting uninstalls of other externally-managed
  packages and leaks a build workaround into product metadata.

### Verify by rebuilding and by the existing container test

The fix is confirmed by rebuilding the image and by the `integration` smoke test
in `tests/mcp/test_container.py`, which builds the repo `Dockerfile` and asserts
the MCP endpoint lists the expected tools. No new test is required; the existing
test is the acceptance check once the build succeeds.

*Alternatives:* a Dockerfile-linting unit test that greps for the flag - brittle
and does not prove the build works.

## Risks / Trade-offs

- [pip installs packages that also exist via apt, so `/usr/local` shadows apt
  versions] → Only the shadowed packages change behavior, and the shadowed set
  is the project's own dependency tree; `apt_pkg`/`debian` are not pip
  dependencies and are not shadowed. Accepted.
- [`--ignore-installed` re-resolves and installs the whole dependency tree,
  slightly enlarging the layer and repeating work] → Build-time cost only;
  `--no-cache-dir` already trades layer caching for size.
- [A future external dependency reintroduces a similar conflict] → The flag
  covers externally-managed packages generally, not just `idna`.
- [`--ignore-installed` can leave duplicate metadata in two site dirs] →
  Harmless for this single-purpose image; the pip-managed tree wins on
  `sys.path`.

## Migration Plan

One-line `Dockerfile` change with a comment explaining the Debian/PEP 668
reason. Rollback is reverting the line. No API, dependency, or data migration;
images are rebuilt from source.

## Open Questions

None.
