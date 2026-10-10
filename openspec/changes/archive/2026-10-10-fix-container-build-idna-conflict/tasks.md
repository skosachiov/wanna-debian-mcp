# Tasks

## 1. Fix the Docker MCP-extra install

- [x] 1.1 In `Dockerfile`, change the MCP install to `RUN pip install --break-system-packages --no-cache-dir --ignore-installed '.[mcp]'` and add a short comment stating that `--ignore-installed` avoids pip trying to uninstall apt-managed packages (e.g. Debian's `python3-idna`) during the `idna>=3.18` upgrade required by `httpx2`. Verify with `grep -n -- '--ignore-installed' Dockerfile` that the flag is on the `'.[mcp]'` install line.

## 2. Verify the image builds and serves MCP

- [x] 2.1 Build the image from the repo `Dockerfile` with an available runtime (`podman build -t wanna-debian-mcp .`, or `docker build`) and verify the build completes with no `uninstall-no-record-file` error. (See design.md - Context for the exact failure being fixed.)
- [x] 2.2 Confirm the runtime contract inside the built image: run `podman run --rm --entrypoint python3 wanna-debian-mcp -c "import apt_pkg, idna; print(idna.__version__)"` (or the docker equivalent) and verify `apt_pkg` imports and the printed `idna` version is `>=3.18`.
- [x] 2.3 Start the built image and verify the containerized server serves the MCP endpoint: run `pytest tests/mcp/test_container.py -m integration` and confirm it lists the expected tools; when no container runtime is available it must skip cleanly rather than fail.

## 3. Align container docs

- [x] 3.1 Review the container sections in `README.md` and `docs/mcp/index.md` and confirm the documented `build`/`run` commands still match the `Dockerfile` after the change; add a one-line note only if the Debian/PEP 668 install behavior is worth surfacing. Verify `pytest tests/mcp/test_docs.py` still passes.

## 4. Integration verification

- [x] 4.1 Run the fast suite and confirm no regressions: `pytest -m "not integration"`. Verify it passes (the container test is excluded and skips where no runtime exists).

## Workflow follow-up

- This fix unblocks the container build/run tasks in `add-debian-mcp-server` (task 5) and `add-podman-mcp-workflow` (tasks 2.2-3.2); re-run those once this change is applied.
- Rebuild the image and re-run `pytest -m integration` after implementation to confirm the end-to-end container path.
- Archive the change once the project's review requirements are satisfied.
