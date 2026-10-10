"""Verify the documentation matches the registered MCP tool schemas."""

import asyncio
from pathlib import Path

from fastmcp import Client

from wanna_debian_mcp.server import create_app

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "mcp" / "index.md"
README = ROOT / "README.md"


def _registered_tools():
    app = create_app(metadata_dir="/tmp")

    async def run():
        async with Client(app) as client:
            return await client.list_tools()

    return asyncio.run(run())


def _schema(tool):
    schema = getattr(tool, "input_schema", None)
    if schema is None:  # pragma: no cover - older FastMCP
        schema = tool.inputSchema
    return schema


def test_docs_cover_every_tool_and_parameter():
    text = DOC.read_text(encoding="utf-8")
    tools = _registered_tools()
    assert tools, "no tools registered"
    for tool in tools:
        assert tool.name in text, f"docs do not mention tool {tool.name!r}"
        for param in _schema(tool).get("properties", {}):
            assert param in text, (
                f"docs do not mention parameter {param!r} of tool {tool.name!r}"
            )


def test_readme_links_to_mcp_docs_and_lists_tools():
    text = README.read_text(encoding="utf-8")
    assert "docs/mcp/index.md" in text
    for tool in _registered_tools():
        assert tool.name in text, f"README does not mention tool {tool.name!r}"
