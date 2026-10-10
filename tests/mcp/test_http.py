"""End-to-end HTTP test: start the server via the documented CLI and use it.

Covers task 4.4 (the documented start command answers a tool-list request)
and task 6.2 (search a package and resolve binaries in one MCP session).
"""

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from fastmcp import Client

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).parent / "data"


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _wait_for_port(port: int, proc: subprocess.Popen, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            output = proc.stdout.read().decode(errors="replace") if proc.stdout else ""
            pytest.fail(f"server exited early:\n{output[-1000:]}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return
        except OSError:
            time.sleep(0.2)
    proc.kill()
    pytest.fail("server did not start listening in time")


@pytest.fixture
def server(tmp_path):
    port = _free_port()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "wanna_debian_mcp.server",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--metadata-dir",
            str(DATA),
        ],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    _wait_for_port(port, proc)
    try:
        yield port
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            proc.kill()


def _metadata_dir(base: str) -> str:
    target = os.path.join(base, "dists", "trixie", "main")
    os.makedirs(target, exist_ok=True)
    path = os.path.join(target, "Packages.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(
            [
                {
                    "package": "foo",
                    "version": "2.0",
                    "dist": "trixie",
                    "comp": "main",
                    "build": "binary-amd64",
                    "arch": "amd64",
                    "source": "foosrc",
                    "source_version": "2.0",
                }
            ],
            handle,
        )
    return base


def test_http_end_to_end(server, tmp_path):
    port = server
    metadata_dir = _metadata_dir(str(tmp_path))

    async def run():
        url = f"http://127.0.0.1:{port}/mcp"
        async with Client(url) as client:
            tools = await client.list_tools()
            search = await client.call_tool(
                "search_packages",
                {"requirements": ["foo"], "metadata_dir": metadata_dir, "latest": True},
            )
            binaries = await client.call_tool(
                "resolve_binaries",
                {"metadata_file": str(DATA / "small_Sources"), "sources": ["app"]},
            )
            return tools, search.data, binaries.data

    tools, search, binaries = asyncio.run(run())
    names = {tool.name for tool in tools}
    assert "search_packages" in names
    assert "resolve_binaries" in names
    assert search["count"] == 1
    assert search["records"][0]["package"] == "foo"
    assert binaries == {"results": [{"source": "app", "binaries": ["app"]}]}
