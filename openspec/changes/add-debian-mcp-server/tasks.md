# Tasks

## 1. Scaffolding and dependencies

- [x] 1.1 Create the `wanna_debian_mcp/` package (`__init__.py`, `server.py`, `tools.py`) with a minimal importable skeleton, and verify with `python3 -c "import wanna_debian_mcp"`.
- [x] 1.2 Add `fastmcp` under `[project.optional-dependencies] mcp` and the `wanna-debian-mcp` console script in `pyproject.toml`; verify `pip install -e '.[mcp]'` succeeds and `wanna-debian-mcp --help` prints usage.
- [x] 1.3 Add a lazy-import guard that reports an actionable install hint (`wanna-debian[mcp]`) when `fastmcp` is missing; verify by importing `server.py` in an environment without fastmcp and observing the message instead of a traceback.

## 2. distro-metadata tools

- [x] 2.1 Add an additive `collect_versions(...)` in `distrotracker` that returns records and make `find_versions` print its result unchanged; verify existing `tests/distrotracker` pass and a new unit test asserts `collect_versions` output for a sample requirement.
- [x] 2.2 Implement metadata workspace/config wiring (`--metadata-dir` / `WANNA_DEBIAN_METADATA_DIR`, default `./metadata`) and the `update_metadata` and `list_distributions` tools; verify with an integration test (marked `integration`) that performs a small metadata update against a Debian base URL and lists distributions.
- [x] 2.3 Implement the `search_packages` tool (requirement list, dist/comp/build/arch filters, by-source, latest/earliest, brief, grep) on top of `collect_versions`; verify unit tests cover satisfied constraint, no-match, unknown package, filtering, latest/earliest selection, and source-oriented search using fixture metadata JSON.
- [x] 2.4 Document the distro-metadata tools (names, arguments, examples) in `docs/` and verify the documented examples match the registered tool schemas.

## 3. dependency-analysis tools

- [x] 3.1 Implement `resolve_source`, `resolve_binaries`, and `resolve_group` tools over `predose.Metadata`; verify unit tests using `tests/predose/data/*_Packages` and `*_Sources` cover known, unknown, and multi-binary cases.
- [x] 3.2 Implement `dependencies` (with depth) and `reverse_dependencies` tools; verify unit tests cover multi-level and depth-one dependency sets and empty/known reverse-dependency cases.
- [x] 3.3 Implement the `toposort` tool with latest-version selection; verify a unit test asserts dependency-respecting order and that repeated calls return an identical ordering.
- [x] 3.4 Document the dependency-analysis tools (names, arguments, examples) in `docs/` and verify the documented examples match the registered tool schemas.

## 4. MCP server surface

- [x] 4.1 Implement the FastMCP app with tool registration and configurable HTTP transport (`--host` default `127.0.0.1`, `--port` default `8000`); verify an in-memory FastMCP client can initialize, list tools, and call one tool.
- [x] 4.2 Add the process-wide concurrency lock around metadata updates/config global access and `apt_pkg.init()` at startup; verify a test issues concurrent update/search calls without corruption.
- [x] 4.3 Add structured error handling so invalid arguments and in-call failures return an error result and the server stays up; verify tests for invalid arguments, a missing metadata file, and a successful call before and after a failed one.
- [x] 4.4 Document how to run the server locally and how tools are exposed in the README/docs, and verify the documented start command launches a server that answers a tool-list request.

## 5. Container

- [ ] 5.1 Add the `Dockerfile` (Debian base, system `python3` + `python3-apt`/`requests`/`debian`, `dctrl-tools`, `jq`, `pip install '.[mcp]'`, `--host 0.0.0.0`, `EXPOSE`, CMD) and verify `docker build` completes and `python3 -c "import apt_pkg"` works inside the image.
- [ ] 5.2 Verify a started container serves the MCP HTTP endpoint without authentication on the exposed port and that `list_distributions`/`resolve_binaries` tools respond.
- [x] 5.3 Document container build/run (and the no-auth exposure warning) in the README/docs and verify the documented commands match the Dockerfile.

## 6. Integration verification

- [x] 6.1 Run the full test suite (`pytest`) and confirm the new unit tests pass and no existing `distrotracker`/`predose`/`toposort` tests regress.
- [x] 6.2 End-to-end check over HTTP: search a package via `search_packages` and resolve a binary via `resolve_binaries` in one session, confirming both structured results against the specs.
