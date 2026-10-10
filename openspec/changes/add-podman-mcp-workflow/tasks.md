# Tasks

## 1. Podman install/build/run documentation

- [x] 1.1 Add a podman section to `docs/mcp/index.md` covering the git install (`pip install --user --break-system-packages git+https://github.com/skosachiov/wanna-debian.git`), `podman build -t wanna-debian-mcp .`, and `podman run --privileged ...`, keeping the existing Docker examples cross-referenced. Verify the commands match the `Dockerfile` (image name, `/data/metadata`, port 8000, `--host 0.0.0.0`).
- [x] 1.2 Explain in that section why `podman run` uses `--privileged` (mounts/build-tooling and metadata writes) and note it can be dropped for read-only analysis calls. Verify a reader can tell which operations need it.
- [x] 1.3 Document how to verify the MCP endpoint from the host (`initialize` + `tools/list` against `http://<host>:8000/mcp`, or an MCP client), including the no-auth exposure warning. Verify the documented endpoint path matches the server's `/mcp` route.
- [x] 1.4 Add a short podman pointer to `README.md` (git install + `podman build`/`podman run --privileged`) linking to `docs/mcp/index.md`. Verify `pytest tests/mcp/test_docs.py` still passes (README still links the docs and lists every tool).

## 2. Container verification test

- [x] 2.1 Add `tests/mcp/test_container.py`, marked `integration`, that selects `podman` then `docker` via `shutil.which` and skips with an actionable message when neither exists. Verify that it skips cleanly on a machine without a container runtime.
- [x] 2.2 In the test, build the image from the repo `Dockerfile`, run it detached on a random published host port with a temporary metadata directory mounted at `/data/metadata`, and assert it matches the commands documented in task 1. Verify the build/run arguments equal the documented ones.
- [ ] 2.3 Poll `http://127.0.0.1:<port>/mcp` with a bounded timeout, perform `initialize` + `tools/list`, assert the expected tools are present, and tear the container down in a `finally` block. Verify `pytest tests/mcp/test_container.py -m integration` passes with a runtime present.

## 3. Integration verification

- [x] 3.1 Run `pytest -m "not integration"` and confirm there are no regressions from this change (`test_docs.py` included).
- [ ] 3.2 Run `pytest -m integration` and confirm the containerized server answers the MCP endpoint via the documented commands.

## Workflow follow-up

- Archive the change once the project's review requirements are satisfied.
