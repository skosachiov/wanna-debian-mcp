"""Entry point and FastMCP application for the wanna-debian MCP server.

The FastMCP dependency is optional (it requires Python >= 3.10).  Importing
this module never imports FastMCP; the import happens lazily when the server
is actually started, so the module stays importable everywhere and a missing
dependency produces an actionable message instead of a traceback.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional, Sequence

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_TRANSPORT = "http"

INSTALL_HINT = (
    "The wanna-debian MCP server requires the optional 'mcp' dependencies "
    "(FastMCP, Python >= 3.10).\n"
    "Install them with:\n"
    "    pip install 'wanna-debian[mcp]'\n"
)


def _require_fastmcp():
    """Import and return the FastMCP module, or exit with an actionable hint."""
    try:
        import fastmcp  # noqa: F401
    except ImportError:
        print(INSTALL_HINT, file=sys.stderr)
        raise SystemExit(1)
    return fastmcp


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for the server."""
    parser = argparse.ArgumentParser(
        prog="wanna-debian-mcp",
        description=(
            "Local, no-authentication MCP server exposing wanna-debian "
            "distrotracker and pre-dose analysis tools."
        ),
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("WANNA_DEBIAN_MCP_HOST", DEFAULT_HOST),
        help="Interface to bind (default: %(default)s)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("WANNA_DEBIAN_MCP_PORT", DEFAULT_PORT)),
        help="Port to listen on (default: %(default)s)",
    )
    parser.add_argument(
        "--transport",
        default=os.environ.get("WANNA_DEBIAN_MCP_TRANSPORT", DEFAULT_TRANSPORT),
        choices=["http", "streamable-http"],
        help="MCP transport to serve (default: %(default)s)",
    )
    parser.add_argument(
        "--metadata-dir",
        default=None,
        help=(
            "Directory used to store and read Debian metadata "
            "(default: $WANNA_DEBIAN_METADATA_DIR or ./metadata)"
        ),
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("WANNA_DEBIAN_MCP_LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: %(default)s)",
    )
    return parser


INSTRUCTIONS = (
    "Local, no-authentication MCP server for Debian distribution analysis. "
    "Use `init_metadata` to create a named metadata workspace and pull its "
    "metadata, and `update_metadata` to refresh an existing workspace (reusing "
    "its stored base URL when none is supplied). Then use `search_packages` to "
    "find package versions by requirement. "
    "`resolve_source`, `resolve_binaries` and `resolve_group` map between "
    "binary and source packages, and `dependencies`, `reverse_dependencies` "
    "and `toposort` analyse dependency graphs."
)


def create_app(metadata_dir: Optional[str] = None):
    """Build the FastMCP application and register every tool.

    Tools fall back to ``metadata_dir`` (resolved from the argument,
    ``$WANNA_DEBIAN_METADATA_DIR`` or ``./metadata``) when the caller does not
    pass one explicitly.
    """
    from fastmcp import FastMCP

    from . import tools

    tools.init_apt()
    resolved_dir = tools.get_metadata_dir(metadata_dir)

    app = FastMCP(
        name="wanna-debian",
        instructions=INSTRUCTIONS,
        mask_error_details=False,
    )

    @app.tool
    def list_distributions(
        base_url: str, no_check_certificate: bool = False
    ) -> dict:
        """List the distributions published at a Debian repository base URL."""
        return tools.list_distributions(base_url, no_check_certificate)

    @app.tool
    def init_metadata(
        base_url: str,
        workspace: str | None = None,
        metadata_dir: str | None = None,
        dist: list[str] | None = None,
        comp: list[str] | None = None,
        build: list[str] | None = None,
        sysarch: str = "amd64",
        no_check_certificate: bool = False,
        force: bool = False,
    ) -> dict:
        """Initialize a named metadata workspace and pull its metadata.

        ``workspace`` is a name under the metadata root (``"debian"`` maps to
        ``<root>/debian``); an absolute path is used as-is.  Mirrors
        ``distrotracker -u -D <workspace> -B <base_url>``.  ``dist`` limits
        which distributions are fetched (default: all); ``comp``/``build``
        limit components and build types.
        """
        return tools.init_metadata(
            base_url=base_url,
            workspace=workspace,
            metadata_dir=metadata_dir or resolved_dir,
            dist=dist,
            comp=comp,
            build=build,
            sysarch=sysarch,
            no_check_certificate=no_check_certificate,
            force=force,
        )

    @app.tool
    def update_metadata(
        base_url: str | None = None,
        workspace: str | None = None,
        metadata_dir: str | None = None,
        dist: list[str] | None = None,
        comp: list[str] | None = None,
        build: list[str] | None = None,
        sysarch: str = "amd64",
        no_check_certificate: bool = False,
        force: bool = False,
    ) -> dict:
        """Refresh a metadata workspace from its stored configuration.

        Omit ``base_url`` to reuse the workspace's stored base URL and filters
        (set them first with ``init_metadata``).  A supplied ``base_url`` must
        match the workspace's stored one.  ``dist``/``comp``/``build`` limit
        the fetch; ``force`` refreshes even when the local copy looks current.
        """
        return tools.update_metadata(
            base_url=base_url,
            workspace=workspace,
            metadata_dir=metadata_dir or resolved_dir,
            dist=dist,
            comp=comp,
            build=build,
            sysarch=sysarch,
            no_check_certificate=no_check_certificate,
            force=force,
        )

    @app.tool
    def search_packages(
        requirements: list[str],
        metadata_dir: str | None = None,
        dist: list[str] | None = None,
        comp: list[str] | None = None,
        build: list[str] | None = None,
        arch: list[str] | None = None,
        by_source: bool = False,
        latest: bool = False,
        earliest: bool = False,
        briefly: bool = False,
        grep: str | None = None,
    ) -> dict:
        """Find package records matching requirement expressions.

        Each requirement may be ``name``, ``name=version`` or
        ``name (op version)``.  Set ``by_source`` to match source package
        names instead of binary package names.
        """
        return tools.search_packages(
            requirements,
            metadata_dir or resolved_dir,
            dist,
            comp,
            build,
            arch,
            by_source,
            latest,
            earliest,
            briefly,
            grep,
        )

    @app.tool
    def resolve_source(
        metadata_file: str,
        packages: list[str],
        add_version: bool = False,
    ) -> dict:
        """Resolve binary package name(s) to their source package."""
        return tools.resolve_source(metadata_file, packages, add_version)

    @app.tool
    def resolve_binaries(
        metadata_file: str,
        sources: list[str],
        add_version: bool = False,
        latest: bool = False,
    ) -> dict:
        """Resolve source package name(s) to the binary packages they build."""
        return tools.resolve_binaries(metadata_file, sources, add_version, latest)

    @app.tool
    def resolve_group(
        metadata_file: str,
        packages: list[str],
        add_version: bool = False,
        latest: bool = False,
    ) -> dict:
        """Resolve the sibling binary packages built from the same source."""
        return tools.resolve_group(metadata_file, packages, add_version, latest)

    @app.tool
    def dependencies(
        metadata_file: str,
        package: str,
        depth: int = 1,
        latest: bool = False,
    ) -> dict:
        """Return the transitive dependency set of a package up to ``depth``."""
        return tools.dependencies(metadata_file, package, depth, latest)

    @app.tool
    def reverse_dependencies(
        metadata_file: str,
        package: str,
        latest: bool = False,
    ) -> dict:
        """Return the packages that directly depend on ``package``."""
        return tools.reverse_dependencies(metadata_file, package, latest)

    @app.tool
    def toposort(
        metadata_file: str,
        packages: list[str],
        latest: bool = False,
    ) -> dict:
        """Return a dependency-respecting ordering of the given packages."""
        return tools.toposort(metadata_file, packages, latest)

    return app


def main(argv: Optional[Sequence[str]] = None) -> None:
    """Parse arguments and run the MCP server."""
    args = build_parser().parse_args(argv)

    # FastMCP (and therefore the server) is only required to actually run.
    _require_fastmcp()

    app = create_app(metadata_dir=args.metadata_dir)
    app.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
