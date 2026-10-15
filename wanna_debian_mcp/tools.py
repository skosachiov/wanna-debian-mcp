"""Tool implementations for the wanna-debian MCP server.

These functions are thin, non-printing wrappers around the existing
``distrotracker`` and ``predose`` logic.  They return structured Python data
(JSON-serializable) so the MCP layer in :mod:`wanna_debian_mcp.server` can
register them as tools.

Design notes (see openspec/changes/add-debian-mcp-server/design.md):
- ``collect_versions`` is the reusable, non-printing core of distrotracker.
- ``update_metadata`` relies on the ``distrotracker`` module-global ``config``;
  access is serialized with a process-wide lock.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import threading
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence

import apt_pkg
import requests

from distrotracker import distrotracker as _dt
from distrotracker.distrotracker import (
    collect_versions,
    get_distributions,
    original_metadata_is_newer,
    update_metadata as _update_metadata,
)
from predose.predose import Metadata, PkgKey

DEFAULT_METADATA_DIR = "./metadata"
ENV_METADATA_DIR = "WANNA_DEBIAN_METADATA_DIR"

_LOCK = threading.RLock()

# Repository-independent baseline for the per-workspace filters, captured from
# ``distrotracker`` before any tool call can mutate its module-global config.
# A workspace that omits a filter resolves to these defaults instead of another
# workspace's persisted values.
_DEFAULT_DIST: List[str] = list(_dt.config["dist"])
_DEFAULT_COMP: List[str] = list(_dt.config["comp"])
_DEFAULT_BUILDS: List[str] = list(_dt.config["builds"])
_DEFAULT_SYSARCH: str = _dt.config["sysarch"]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def init_apt() -> None:
    """Initialize ``apt_pkg`` for Debian version comparison (idempotent)."""
    try:
        apt_pkg.init_system()
    except apt_pkg.Error:
        # Already initialized (e.g. ``predose`` initializes it at import time).
        pass


def get_metadata_dir(metadata_dir: Optional[str] = None) -> str:
    """Resolve the metadata workspace directory.

    Priority: explicit argument, then ``$WANNA_DEBIAN_METADATA_DIR``, then
    ``./metadata``.  The result is always absolute.
    """
    candidate = metadata_dir or os.environ.get(ENV_METADATA_DIR) or DEFAULT_METADATA_DIR
    return os.path.abspath(os.path.expanduser(candidate))


def get_workspace_dir(
    workspace: Optional[str] = None, metadata_dir: Optional[str] = None
) -> str:
    """Resolve a metadata workspace directory.

    The server metadata root is ``metadata_dir``, else
    ``$WANNA_DEBIAN_METADATA_DIR``, else ``./metadata``.  A relative
    ``workspace`` name is joined under that root (``workspace="debian"`` maps
    to ``<root>/debian``); an absolute ``workspace`` is used as-is.  With no
    ``workspace`` the root itself is the workspace.
    """
    root = get_metadata_dir(metadata_dir)
    if not workspace:
        return root
    expanded = os.path.expanduser(workspace)
    if os.path.isabs(expanded):
        return os.path.abspath(expanded)
    return os.path.join(root, expanded)


def _config_file(workspace_dir: str) -> str:
    """Return the path of the workspace configuration file."""
    return os.path.join(workspace_dir, _dt.config["config_file"])


def _read_workspace_config(workspace_dir: str) -> Optional[Dict[str, Any]]:
    """Read the workspace ``config.json``, or ``None`` when it is absent."""
    path = _config_file(workspace_dir)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def find_metadata_files(metadata_dir: str) -> List[str]:
    """Return the metadata index JSON files stored under ``metadata_dir``."""
    files: List[str] = []
    if not os.path.isdir(metadata_dir):
        return files
    excluded = {_dt.config["config_file"], _dt.config["index_file"]}
    for root, _dirs, names in os.walk(metadata_dir):
        for name in names:
            if name.endswith(".json") and name not in excluded:
                files.append(os.path.join(root, name))
    files.sort()
    return files


def _normalize_base_url(base_url: str) -> str:
    if not base_url or not isinstance(base_url, str):
        raise ValueError("base_url is required")
    return base_url if base_url.endswith("/") else base_url + "/"


def _new_session(ssl_verify: bool = True) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {"Cache-Control": "no-cache", "Pragma": "no-cache", "Expires": "0"}
    )
    session.verify = ssl_verify
    return session


def _split_lines(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [line for line in value.splitlines() if line.strip()]


def _split_name_version(spec: str) -> tuple:
    """Split ``name`` or ``name=version`` (as used by the pre-dose CLI)."""
    if not spec or not isinstance(spec, str):
        raise ValueError("package name is required")
    parts = spec.split("=", 1)
    name = parts[0].strip()
    version = parts[1].strip() if len(parts) > 1 else ""
    if not name:
        raise ValueError(f"invalid package specification: {spec!r}")
    return name, version


def _parse_topo_line(line: str) -> tuple:
    try:
        parsed = ast.literal_eval(line)
        if isinstance(parsed, tuple) and len(parsed) == 2:
            return int(parsed[0]), str(parsed[1])
    except (ValueError, SyntaxError):
        pass
    return 0, line


# ---------------------------------------------------------------------------
# distro-metadata tools
# ---------------------------------------------------------------------------

def list_distributions(
    base_url: str, no_check_certificate: bool = False
) -> Dict[str, Any]:
    """List the distributions available at a Debian repository base URL."""
    init_apt()
    base = _normalize_base_url(base_url)
    session = _new_session(not no_check_certificate)
    with _LOCK:
        distributions = get_distributions(base + "dists/", session)
    return {"base_url": base, "distributions": distributions}


def _pull_into_workspace(
    resolved_dir: str,
    base: str,
    dist: Optional[Sequence[str]],
    comp: Optional[Sequence[str]],
    build: Optional[Sequence[str]],
    sysarch: str,
    no_check_certificate: bool,
    force: bool,
) -> Dict[str, Any]:
    """Configure the distrotracker globals, pull metadata, and persist config.

    Shared by :func:`init_metadata` and :func:`update_metadata` so both modes
    use one refresh path.  Serialized with the process-wide ``_LOCK`` because
    ``distrotracker.distrotracker.config`` is a module global.
    """
    session = _new_session(not no_check_certificate)
    hashes: set = set()

    with _LOCK:
        cfg = _dt.config
        # Resolve every filter from the explicit argument or the
        # repository-independent baseline, then assign all of them
        # unconditionally so the workspace never inherits another workspace's
        # persisted values.
        resolved_dist = list(dist) if dist else list(_DEFAULT_DIST)
        resolved_comp = list(comp) if comp else list(_DEFAULT_COMP)
        resolved_builds = list(build) if build else list(_DEFAULT_BUILDS)
        cfg["base_url"] = base
        cfg["ssl_verify"] = not no_check_certificate
        cfg["local_dir"] = [resolved_dir]
        cfg["sysarch"] = sysarch or _DEFAULT_SYSARCH
        cfg["dist"] = resolved_dist
        cfg["comp"] = resolved_comp
        cfg["builds"] = resolved_builds
        components = resolved_comp
        builds = resolved_builds
        dists = resolved_dist
        cfg["timestamp"] = str(time.time())

        config_file = _config_file(resolved_dir)
        need_update = force or not os.path.exists(config_file)
        if not need_update:
            need_update = original_metadata_is_newer(base, resolved_dir, session, hashes)

        if need_update:
            _update_metadata(
                base, resolved_dir, dists or None, components, builds, session, hashes
            )
        with open(config_file, "w", encoding="utf-8") as handle:
            json.dump(cfg, handle, indent=4)

    return {
        "base_url": base,
        "metadata_dir": resolved_dir,
        "updated": bool(need_update),
        "distributions": dists or None,
        "components": components,
        "builds": builds,
    }


def init_metadata(
    base_url: str,
    workspace: Optional[str] = None,
    metadata_dir: Optional[str] = None,
    dist: Optional[Sequence[str]] = None,
    comp: Optional[Sequence[str]] = None,
    build: Optional[Sequence[str]] = None,
    sysarch: str = "amd64",
    no_check_certificate: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    """Initialize a named metadata workspace and perform its initial pull.

    ``base_url`` is required.  The configuration (base URL, filters,
    architecture and TLS setting) is persisted as ``config.json`` in the
    resolved workspace directory, mirroring
    ``distrotracker -u -D <workspace> -B <base_url>``.
    """
    init_apt()
    if not base_url:
        raise ValueError(
            "base_url is required to initialize a metadata workspace"
        )
    base = _normalize_base_url(base_url)
    resolved_dir = get_workspace_dir(workspace, metadata_dir)
    stored = _read_workspace_config(resolved_dir)
    if (
        stored
        and stored.get("base_url")
        and _normalize_base_url(stored["base_url"]) != base
    ):
        raise ValueError(
            f"workspace {resolved_dir!r} is already configured for base URL "
            f"{stored['base_url']!r}; refusing to initialize it from {base!r}. "
            "Use update_metadata to refresh an existing workspace."
        )
    os.makedirs(resolved_dir, exist_ok=True)
    result = _pull_into_workspace(
        resolved_dir, base, dist, comp, build, sysarch, no_check_certificate, force
    )
    result["workspace"] = workspace
    return result


def update_metadata(
    base_url: Optional[str] = None,
    workspace: Optional[str] = None,
    metadata_dir: Optional[str] = None,
    dist: Optional[Sequence[str]] = None,
    comp: Optional[Sequence[str]] = None,
    build: Optional[Sequence[str]] = None,
    sysarch: str = "amd64",
    no_check_certificate: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    """Refresh a Debian metadata workspace.

    When ``base_url`` is omitted the workspace's stored ``config.json`` supplies
    the base URL and filters.  A supplied ``base_url`` for an already
    initialized workspace must match the stored one; a workspace with no stored
    configuration and no ``base_url`` is an error (initialize it with
    :func:`init_metadata` first).
    """
    init_apt()
    resolved_dir = get_workspace_dir(workspace, metadata_dir)
    stored = _read_workspace_config(resolved_dir)

    if base_url:
        base = _normalize_base_url(base_url)
        if (
            stored
            and stored.get("base_url")
            and _normalize_base_url(stored["base_url"]) != base
        ):
            raise ValueError(
                f"workspace {resolved_dir!r} is configured for base URL "
                f"{stored['base_url']!r}; refusing to update it from {base!r}"
            )
    elif stored and stored.get("base_url"):
        base = _normalize_base_url(stored["base_url"])
    else:
        raise ValueError(
            f"workspace {resolved_dir!r} has no stored configuration; initialize "
            "it first with init_metadata(base_url=..., workspace=...) or supply "
            "a base_url"
        )

    if stored:
        if dist is None:
            dist = stored.get("dist")
        if comp is None:
            comp = stored.get("comp")
        if build is None:
            build = stored.get("builds")
        if sysarch == "amd64" and stored.get("sysarch"):
            sysarch = stored["sysarch"]
        if base_url is None:
            no_check_certificate = not stored.get(
                "ssl_verify", not no_check_certificate
            )

    os.makedirs(resolved_dir, exist_ok=True)
    result = _pull_into_workspace(
        resolved_dir, base, dist, comp, build, sysarch, no_check_certificate, force
    )
    result["workspace"] = workspace
    return result


def search_packages(
    requirements: Sequence[str],
    metadata_dir: Optional[str] = None,
    dist: Optional[Sequence[str]] = None,
    comp: Optional[Sequence[str]] = None,
    build: Optional[Sequence[str]] = None,
    arch: Optional[Sequence[str]] = None,
    by_source: bool = False,
    latest: bool = False,
    earliest: bool = False,
    briefly: bool = False,
    grep: Optional[str] = None,
    files: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Find package records satisfying requirement expressions.

    Each requirement is ``name``, ``name=version`` or ``name (op version)``
    (for example ``libpython3.13 (>= 3.13.0~rc3)``).
    """
    init_apt()
    if latest and earliest:
        raise ValueError("'latest' and 'earliest' are mutually exclusive")
    if isinstance(requirements, str):
        requirements = [requirements]
    if not requirements:
        raise ValueError("at least one requirement is required")

    resolved_dir = get_metadata_dir(metadata_dir)
    filenames = list(files) if files else find_metadata_files(resolved_dir)
    if not filenames:
        raise FileNotFoundError(
            f"No metadata JSON files found in {resolved_dir}; run update_metadata first"
        )

    selection = "latest" if latest else ("earliest" if earliest else None)
    records = collect_versions(
        list(requirements),
        filenames,
        dist=list(dist) if dist else None,
        comp=list(comp) if comp else None,
        build=list(build) if build else None,
        arch=list(arch) if arch else None,
        briefly=briefly,
        index_key="source" if by_source else "package",
        selection=selection,
        grep_pattern=grep,
    )
    return {"count": len(records), "records": records}


# ---------------------------------------------------------------------------
# dependency-analysis tools
# ---------------------------------------------------------------------------

def resolve_source(
    metadata_file: str,
    packages: Sequence[str],
    add_version: bool = False,
) -> Dict[str, Any]:
    """Resolve binary package name(s) to their source package."""
    init_apt()
    meta = Metadata.from_file(metadata_file)
    results = []
    for spec in packages:
        name, version = _split_name_version(spec)
        source = meta.resolve_src(PkgKey(name, version), add_version)
        results.append({"package": spec, "source": source or None})
    return {"results": results}


def resolve_binaries(
    metadata_file: str,
    sources: Sequence[str],
    add_version: bool = False,
    latest: bool = False,
) -> Dict[str, Any]:
    """Resolve source package name(s) to the binary packages they build."""
    init_apt()
    meta = Metadata.from_file(metadata_file)
    if latest:
        meta.keep_latest_src()
    results = []
    for spec in sources:
        name, version = _split_name_version(spec)
        binaries = _split_lines(meta.resolve_bin(PkgKey(name, version), add_version))
        results.append({"source": spec, "binaries": binaries})
    return {"results": results}


def resolve_group(
    metadata_file: str,
    packages: Sequence[str],
    add_version: bool = False,
    latest: bool = False,
) -> Dict[str, Any]:
    """Resolve the sibling binary packages built from the same source."""
    init_apt()
    meta = Metadata.from_file(metadata_file)
    if latest:
        meta.keep_latest()
    results = []
    for spec in packages:
        name, version = _split_name_version(spec)
        group = _split_lines(meta.resolve_group(PkgKey(name, version), add_version))
        results.append({"package": spec, "group": group})
    return {"results": results}


def dependencies(
    metadata_file: str,
    package: str,
    depth: int = 1,
    latest: bool = False,
) -> Dict[str, Any]:
    """Return the transitive dependency set of a package up to ``depth``."""
    init_apt()
    if depth < 1:
        raise ValueError("depth must be >= 1")
    meta = Metadata.from_file(metadata_file)
    if latest:
        meta.keep_latest()
    name, version = _split_name_version(package)
    found = set(_split_lines(meta.depends(PkgKey(name, version), int(depth))))
    found.discard(name)
    return {"package": package, "depth": int(depth), "dependencies": sorted(found)}


def reverse_dependencies(
    metadata_file: str,
    package: str,
    latest: bool = False,
) -> Dict[str, Any]:
    """Return the packages that directly depend on ``package``."""
    init_apt()
    meta = Metadata.from_file(metadata_file)
    if latest:
        meta.keep_latest()
    name, _version = _split_name_version(package)
    dependents = sorted(set(_split_lines(meta.rdepends(name))))
    return {"package": package, "dependents": dependents}


def toposort(
    metadata_file: str,
    packages: Sequence[str],
    latest: bool = False,
    dot_file: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a dependency-respecting ordering for a set of packages."""
    init_apt()
    if isinstance(packages, str):
        packages = [packages]
    if not packages:
        raise ValueError("at least one package is required")
    meta = Metadata.from_file(metadata_file)
    if latest:
        meta.keep_latest()

    pkg_set = {PkgKey(*_split_name_version(spec)) for spec in packages}
    raw = meta.toposort(pkg_set, dot_file)
    order = [
        {"level": level, "package": name}
        for level, name in (_parse_topo_line(line) for line in _split_lines(raw))
    ]
    order.sort(key=lambda item: (item["level"], item["package"]))
    return {"order": order}
