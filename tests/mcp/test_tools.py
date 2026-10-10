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


def test_get_workspace_dir_default_is_root(monkeypatch, tmp_path):
    monkeypatch.setenv(tools.ENV_METADATA_DIR, str(tmp_path))
    assert tools.get_workspace_dir() == tools.get_metadata_dir() == str(tmp_path.resolve())


def test_get_workspace_dir_named_under_root(tmp_path):
    root = str(tmp_path)
    assert tools.get_workspace_dir("debian", root) == os.path.join(root, "debian")


def test_get_workspace_dir_uses_env_root(monkeypatch, tmp_path):
    monkeypatch.setenv(tools.ENV_METADATA_DIR, str(tmp_path))
    assert tools.get_workspace_dir("debian") == os.path.join(str(tmp_path), "debian")


def test_get_workspace_dir_absolute_workspace(tmp_path):
    workspace = tmp_path / "elsewhere"
    root = tmp_path / "root"
    assert tools.get_workspace_dir(str(workspace), str(root)) == str(workspace)


# ---------------------------------------------------------------------------
# distro-metadata tools
# ---------------------------------------------------------------------------

def _noop_update(*args, **kwargs):
    """Stand-in for the network pull; records nothing."""


def test_init_metadata_writes_config_and_pulls(monkeypatch, tmp_path):
    calls = []

    def fake_update(base, local_dir, dist, comp, build, session, hashes):
        calls.append((base, local_dir, dist, comp, build))

    monkeypatch.setattr(tools, "_update_metadata", fake_update)
    result = tools.init_metadata(
        "http://ftp.debian.org/debian/",
        workspace="debian",
        metadata_dir=str(tmp_path),
        dist=["trixie"],
        comp=["main"],
        build=["binary-amd64"],
    )

    workspace = os.path.join(str(tmp_path), "debian")
    assert result["metadata_dir"] == workspace
    assert result["base_url"] == "http://ftp.debian.org/debian/"
    assert result["workspace"] == "debian"
    assert result["updated"] is True

    with open(os.path.join(workspace, "config.json"), encoding="utf-8") as handle:
        config = json.load(handle)
    assert config["base_url"] == "http://ftp.debian.org/debian/"
    assert config["local_dir"] == [workspace]
    assert config["dist"] == ["trixie"]
    assert config["comp"] == ["main"]
    assert config["builds"] == ["binary-amd64"]

    assert calls == [
        (
            "http://ftp.debian.org/debian/",
            workspace,
            ["trixie"],
            ["main"],
            ["binary-amd64"],
        )
    ]


def test_init_metadata_requires_base_url(tmp_path):
    workspace = os.path.join(str(tmp_path), "debian")
    with pytest.raises(ValueError):
        tools.init_metadata("", workspace="debian", metadata_dir=str(tmp_path))
    assert not os.path.exists(os.path.join(workspace, "config.json"))


def test_update_metadata_reuses_stored_config(monkeypatch, tmp_path):
    monkeypatch.setattr(tools, "_update_metadata", _noop_update)
    workspace = os.path.join(str(tmp_path), "debian")
    os.makedirs(workspace)
    with open(os.path.join(workspace, "config.json"), "w", encoding="utf-8") as handle:
        json.dump(
            {
                "base_url": "http://example.org/debian/",
                "ssl_verify": True,
                "local_dir": [workspace],
                "sysarch": "amd64",
                "dist": ["trixie"],
                "comp": ["main"],
                "builds": ["binary-amd64"],
            },
            handle,
        )

    result = tools.update_metadata(
        workspace="debian", metadata_dir=str(tmp_path), force=True
    )
    assert result["base_url"] == "http://example.org/debian/"
    assert result["distributions"] == ["trixie"]
    assert result["components"] == ["main"]
    assert result["builds"] == ["binary-amd64"]


def test_update_metadata_uninitialized_without_url_raises(tmp_path):
    workspace = os.path.join(str(tmp_path), "debian")
    with pytest.raises(ValueError) as excinfo:
        tools.update_metadata(workspace="debian", metadata_dir=str(tmp_path))
    assert "init_metadata" in str(excinfo.value)
    assert not os.path.exists(os.path.join(workspace, "config.json"))


def test_update_metadata_with_url_initializes_config(monkeypatch, tmp_path):
    monkeypatch.setattr(tools, "_update_metadata", _noop_update)
    result = tools.update_metadata(
        "http://example.org/debian/",
        workspace="debian",
        metadata_dir=str(tmp_path),
        force=True,
    )
    workspace = os.path.join(str(tmp_path), "debian")
    assert result["base_url"] == "http://example.org/debian/"
    with open(os.path.join(workspace, "config.json"), encoding="utf-8") as handle:
        assert json.load(handle)["base_url"] == "http://example.org/debian/"


def test_update_metadata_rejects_conflicting_url(monkeypatch, tmp_path):
    monkeypatch.setattr(tools, "_update_metadata", _noop_update)
    workspace = os.path.join(str(tmp_path), "debian")
    os.makedirs(workspace)
    stored = {
        "base_url": "http://example.org/debian/",
        "ssl_verify": True,
        "local_dir": [workspace],
        "sysarch": "amd64",
        "comp": ["main"],
        "builds": ["binary-amd64"],
    }
    with open(os.path.join(workspace, "config.json"), "w", encoding="utf-8") as handle:
        json.dump(stored, handle)

    with pytest.raises(ValueError):
        tools.update_metadata(
            "http://other.example.org/debian/",
            workspace="debian",
            metadata_dir=str(tmp_path),
            force=True,
        )

    with open(os.path.join(workspace, "config.json"), encoding="utf-8") as handle:
        assert json.load(handle) == stored


def test_update_metadata_positional_base_url_still_works(monkeypatch, tmp_path):
    monkeypatch.setattr(tools, "_update_metadata", _noop_update)
    result = tools.update_metadata(
        "http://example.org/debian/", metadata_dir=str(tmp_path), force=True
    )
    assert result["base_url"] == "http://example.org/debian/"


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
