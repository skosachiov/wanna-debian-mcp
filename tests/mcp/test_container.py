"""Build the container image and verify the MCP HTTP endpoint (integration).

Marked ``integration``: the test builds the repository ``Dockerfile`` with
podman (preferred) or docker, runs the image detached on a random published
port with a temporary metadata directory, polls the MCP endpoint at ``/mcp``,
and asserts the expected tools are listed.  It skips with an actionable message
when no container runtime is installed.

The commands mirror the documented container workflow in ``docs/mcp/index.md``
and ``README.md`` so the docs stay honest; the module asserts that link before
building.
"""

from __future__ import annotations

import asyncio
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest
from fastmcp import Client

ROOT = Path(__file__).resolve().parents[2]

# Keep these in sync with the documented container commands (docs/mcp/index.md,
# README.md) and the Dockerfile.
IMAGE_NAME = "wanna-debian-mcp"
IMAGE = f"{IMAGE_NAME}:openspec-test"
CONTAINER_PORT = 8000
METADATA_MOUNT = "/data/metadata"
ENDPOINT_PATH = "/mcp"

EXPECTED_TOOLS = {
    "list_distributions",
    "init_metadata",
    "update_metadata",
    "search_packages",
    "resolve_source",
    "resolve_binaries",
    "resolve_group",
    "dependencies",
    "reverse_dependencies",
    "toposort",
}

pytestmark = pytest.mark.integration


def _runtime() -> str:
    """Return the container runtime to use, preferring podman, or skip."""
    for name in ("podman", "docker"):
        if shutil.which(name):
            return name
    pytest.skip(
        "no container runtime found; install podman or docker to run this "
        "integration test"
    )


def _free_port() -> int:
    """Reserve and release a loopback port for the published container port."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _assert_commands_match_docs() -> None:
    """Fail if the docs no longer show the commands this test runs."""
    docs = (ROOT / "docs" / "mcp" / "index.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert f"podman build -t {IMAGE_NAME} ." in docs
    assert f"-p {CONTAINER_PORT}:{CONTAINER_PORT}" in docs
    assert METADATA_MOUNT in docs
    assert "--privileged" in docs
    assert "podman build" in readme and "--privileged" in readme


def _list_tool_names(port: int) -> set[str]:
    async def run() -> set[str]:
        async with Client(f"http://127.0.0.1:{port}{ENDPOINT_PATH}") as client:
            tools = await client.list_tools()
            return {tool.name for tool in tools}

    return asyncio.run(run())


def _wait_for_tools(
    runtime: str, container: str, port: int, timeout: float = 120.0
) -> set[str]:
    """Poll the MCP endpoint until it lists tools, or fail with container logs."""
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        inspect = subprocess.run(
            [runtime, "inspect", "-f", "{{.State.Running}}", container],
            capture_output=True,
            text=True,
        )
        if inspect.returncode != 0 or inspect.stdout.strip() != "true":
            logs = subprocess.run(
                [runtime, "logs", container], capture_output=True, text=True
            )
            pytest.fail(
                "container exited before serving MCP:\n"
                f"{logs.stdout}\n{logs.stderr}"
            )
        try:
            names = _list_tool_names(port)
            if names:
                return names
        except Exception as exc:  # connection refused while starting up
            last_error = exc
        time.sleep(1.0)
    pytest.fail(f"MCP endpoint did not become ready on port {port}: {last_error}")


def test_container_serves_mcp_endpoint(tmp_path):
    _assert_commands_match_docs()

    runtime = _runtime()

    # Build exactly as documented: the repo Dockerfile as the build context.
    subprocess.run(
        [runtime, "build", "-t", IMAGE, "."],
        cwd=str(ROOT),
        check=True,
        timeout=1800,
    )

    port = _free_port()

    # Run exactly as documented: privileged, detached, random published port,
    # and a temporary metadata directory at the image's workspace.
    container = subprocess.run(
        [
            runtime,
            "run",
            "--privileged",
            "-d",
            "--rm",
            "-p",
            f"127.0.0.1:{port}:{CONTAINER_PORT}",
            "-v",
            f"{tmp_path}:{METADATA_MOUNT}:Z",
            IMAGE,
        ],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    try:
        names = _wait_for_tools(runtime, container, port)
        assert EXPECTED_TOOLS <= names, f"missing tools: {EXPECTED_TOOLS - names}"
    finally:
        subprocess.run(
            [runtime, "rm", "-f", container],
            capture_output=True,
        )
