"""Unit tests for the wanna-debian MCP tool implementations."""

import json
import os
from pathlib import Path

import pytest

from wanna_debian_mcp import tools

DATA_DIR = Path(__file__).parent / "data"
SMALL_PACKAGES = str(DATA_DIR / "small_Packages")
SMALL_SOURCES = str(DATA_DIR / "small_Sources")


# ---------------------------------------------------------------------------
# Workspace / config helpers
# ---------------------------------------------------------------------------

def test_get_metadata_dir_explicit(tmp_path):
    assert tools.get_metadata_dir(str(tmp_path)) == str(tmp_path.resolve())


def test_get_metadata_dir_env(monkeypatch, tmp_path):
    monkeypatch.setenv(tools.ENV_METADATA_DIR, str(tmp_path))
    assert tools.get_metadata_dir() == str(tmp_path.resolve())


def test_get_metadata_dir_default(monkeypatch):
    monkeypatch.delenv(tools.ENV_METADATA_DIR, raising=False)
    assert tools.get_metadata_dir() == os.path.abspath("./metadata")


# ---------------------------------------------------------------------------
# distro-metadata tools
# ---------------------------------------------------------------------------

def _write_metadata_dir(base):
    target = os.path.join(base, "dists", "trixie", "main", "binary-amd64")
    os.makedirs(target, exist_ok=True)
    path = os.path.join(target, "Packages.json")
    records = [
        {
            "package": "foo",
            "version": "1.0",
            "dist": "trixie",
            "comp": "main",
            "build": "binary-amd64",
            "arch": "amd64",
            "source": "foosrc",
            "source_version": "1.0",
        },
        {
            "package": "foo",
            "version": "2.0",
            "dist": "trixie",
            "comp": "main",
            "build": "binary-amd64",
            "arch": "amd64",
            "source": "foosrc",
            "source_version": "2.0",
        },
        {
            "package": "bar",
            "version": "1.0",
            "dist": "sid",
            "comp": "contrib",
            "build": "binary-amd64",
            "arch": "amd64",
            "source": "barsrc",
            "source_version": "1.0",
        },
    ]
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(records, handle)
    return base


def test_search_packages_latest(tmp_path):
    md = _write_metadata_dir(str(tmp_path))
    result = tools.search_packages(["foo"], metadata_dir=md, latest=True)
    assert result["count"] == 1
    assert result["records"][0]["version"] == "2.0"


def test_search_packages_by_source(tmp_path):
    md = _write_metadata_dir(str(tmp_path))
    result = tools.search_packages(["foosrc"], metadata_dir=md, by_source=True)
    assert result["count"] == 2
    assert {r["package"] for r in result["records"]} == {"foo"}


def test_search_packages_filters(tmp_path):
    md = _write_metadata_dir(str(tmp_path))
    result = tools.search_packages(["bar"], metadata_dir=md, comp=["contrib"])
    assert result["count"] == 1
    assert result["records"][0]["dist"] == "sid"


def test_search_packages_earliest(tmp_path):
    md = _write_metadata_dir(str(tmp_path))
    result = tools.search_packages(["foo"], metadata_dir=md, earliest=True)
    assert result["count"] == 1
    assert result["records"][0]["version"] == "1.0"


def test_search_packages_constraint(tmp_path):
    md = _write_metadata_dir(str(tmp_path))
    result = tools.search_packages(["foo (>= 2.0)"], metadata_dir=md)
    assert [r["version"] for r in result["records"]] == ["2.0"]


def test_search_packages_unknown_name_returns_empty(tmp_path):
    md = _write_metadata_dir(str(tmp_path))
    result = tools.search_packages(["nosuchpackage"], metadata_dir=md)
    assert result == {"count": 0, "records": []}


def test_search_packages_no_metadata_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        tools.search_packages(["foo"], metadata_dir=str(tmp_path))


def test_search_packages_mutually_exclusive_selection(tmp_path):
    md = _write_metadata_dir(str(tmp_path))
    with pytest.raises(ValueError):
        tools.search_packages(["foo"], metadata_dir=md, latest=True, earliest=True)


# ---------------------------------------------------------------------------
# dependency-analysis tools
# ---------------------------------------------------------------------------

def test_resolve_source():
    result = tools.resolve_source(SMALL_PACKAGES, ["alpha"])
    assert result["results"] == [{"package": "alpha", "source": "alpha-src"}]


def test_resolve_source_unknown():
    result = tools.resolve_source(SMALL_PACKAGES, ["nosuchpackage"])
    assert result["results"] == [{"package": "nosuchpackage", "source": None}]


def test_resolve_source_add_version():
    result = tools.resolve_source(SMALL_PACKAGES, ["alpha=1.0"], add_version=True)
    assert result["results"][0]["source"] == "alpha-src=1.0"


def test_resolve_binaries():
    result = tools.resolve_binaries(SMALL_SOURCES, ["app"])
    assert result["results"] == [{"source": "app", "binaries": ["app"]}]


def test_resolve_binaries_unknown():
    result = tools.resolve_binaries(SMALL_SOURCES, ["nosuchpackage"])
    assert result["results"] == [{"source": "nosuchpackage", "binaries": []}]


def test_resolve_group():
    result = tools.resolve_group(SMALL_PACKAGES, ["alpha"])
    assert result["results"][0]["group"] == ["alpha", "alpha-dev"]


def test_resolve_group_multi_binary():
    result = tools.resolve_group(SMALL_PACKAGES, ["alpha-dev"])
    assert result["results"][0]["group"] == ["alpha", "alpha-dev"]


def test_dependencies():
    result = tools.dependencies(SMALL_PACKAGES, "alpha", depth=2)
    assert result["dependencies"] == ["beta"]


def test_dependencies_depth_one():
    result = tools.dependencies(SMALL_PACKAGES, "alpha", depth=1)
    assert result["dependencies"] == ["beta"]


def test_dependencies_empty():
    result = tools.dependencies(SMALL_PACKAGES, "beta", depth=1)
    assert result["dependencies"] == []


def test_reverse_dependencies():
    result = tools.reverse_dependencies(SMALL_PACKAGES, "beta")
    assert result["dependents"] == ["alpha"]


def test_reverse_dependencies_empty():
    result = tools.reverse_dependencies(SMALL_PACKAGES, "alpha")
    assert result["dependents"] == []


def test_toposort_respects_dependency_order():
    result = tools.toposort(SMALL_SOURCES, ["app", "liba", "libb"])
    names = [entry["package"] for entry in result["order"]]
    assert names.index("libb") < names.index("liba") < names.index("app")


def test_toposort_is_repeatable():
    first = tools.toposort(SMALL_SOURCES, ["app", "liba", "libb"])
    second = tools.toposort(SMALL_SOURCES, ["app", "liba", "libb"])
    assert first == second


def test_toposort_requires_packages():
    with pytest.raises(ValueError):
        tools.toposort(SMALL_SOURCES, [])
