"""Tests for the FastMCP application wiring (tools discovered over the client)."""

import asyncio
from pathlib import Path

import fastmcp
import pytest
from fastmcp import Client

from wanna_debian_mcp.server import build_parser, create_app

DATA_DIR = Path(__file__).parent / "data"
SMALL_PACKAGES = str(DATA_DIR / "small_Packages")

EXPECTED_TOOLS = {
    "list_distributions",
    "update_metadata",
    "search_packages",
    "resolve_source",
    "resolve_binaries",
    "resolve_group",
    "dependencies",
    "reverse_dependencies",
    "toposort",
}


@pytest.fixture
def app(tmp_path):
    return create_app(metadata_dir=str(tmp_path))


def _run(coro):
    return asyncio.run(coro)


def test_parser_defaults_to_loopback():
    args = build_parser().parse_args([])
    assert args.host == "127.0.0.1"
    assert args.port == 8000
    assert args.transport == "http"


def test_parser_accepts_overrides():
    args = build_parser().parse_args(
        ["--host", "0.0.0.0", "--port", "9001", "--metadata-dir", "/data"]
    )
    assert (args.host, args.port, args.metadata_dir) == ("0.0.0.0", 9001, "/data")


def test_all_tools_are_discoverable(app):
    async def run():
        async with Client(app) as client:
            return await client.list_tools()

    names = {tool.name for tool in _run(run())}
    assert EXPECTED_TOOLS <= names


def test_tool_call_returns_structured_data(app):
    async def run():
        async with Client(app) as client:
            return await client.call_tool(
                "resolve_source",
                {"metadata_file": SMALL_PACKAGES, "packages": ["alpha"]},
            )

    result = _run(run())
    assert result.data == {"results": [{"package": "alpha", "source": "alpha-src"}]}


def test_invalid_arguments_return_error_and_server_stays_up(app):
    async def run():
        async with Client(app) as client:
            before = await client.call_tool(
                "resolve_source",
                {"metadata_file": SMALL_PACKAGES, "packages": ["alpha"]},
            )
            bad = await client.call_tool(
                "search_packages",
                {"requirements": ["foo"], "metadata_dir": "/does/not/exist"},
                raise_on_error=False,
            )
            after = await client.call_tool(
                "resolve_source",
                {"metadata_file": SMALL_PACKAGES, "packages": ["beta"]},
            )
            return before, bad, after

    before, bad, after = _run(run())
    assert before.data == {"results": [{"package": "alpha", "source": "alpha-src"}]}
    assert bad.is_error is True
    assert after.data == {"results": [{"package": "beta", "source": "beta-src"}]}


def test_schema_violation_returns_error(app):
    async def run():
        async with Client(app) as client:
            return await client.call_tool(
                "search_packages", {"requirements": 12345}, raise_on_error=False
            )

    result = _run(run())
    assert result.is_error is True
