"""Tests for the additive ``collect_versions`` helper in distrotracker."""

import json
import os
import tempfile

from distrotracker import collect_versions


SAMPLE = [
    {
        "package": "libtest",
        "version": "1.5.0",
        "dist": "trixie",
        "comp": "main",
        "build": "binary-amd64",
        "arch": "amd64",
        "source": "libtest",
        "source_version": "1.5.0",
        "depends": "abc12345",
    },
    {
        "package": "libtest",
        "version": "0.9.0",
        "dist": "trixie",
        "comp": "main",
        "build": "binary-amd64",
        "arch": "amd64",
        "source": "libtest",
        "source_version": "0.9.0",
        "depends": "def67890",
    },
    {
        "package": "other",
        "version": "3.0.0",
        "dist": "sid",
        "comp": "main",
        "build": "binary-amd64",
        "arch": "amd64",
        "source": "other",
        "source_version": "3.0.0",
        "depends": "aaa11111",
    },
]


def _write_index(tmp_path):
    path = os.path.join(tmp_path, "main.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(SAMPLE, f)
    return path


def test_collect_versions_satisfied_constraint(tmp_path):
    path = _write_index(str(tmp_path))
    records = collect_versions(["libtest (>= 1.0.0)"], [path])
    versions = sorted(r["version"] for r in records)
    assert versions == ["1.5.0"]


def test_collect_versions_all_matching_without_constraint(tmp_path):
    path = _write_index(str(tmp_path))
    records = collect_versions(["libtest"], [path])
    assert len(records) == 2


def test_collect_versions_latest_selection(tmp_path):
    path = _write_index(str(tmp_path))
    records = collect_versions(["libtest"], [path], selection="latest")
    assert [r["version"] for r in records] == ["1.5.0"]


def test_collect_versions_dist_filter(tmp_path):
    path = _write_index(str(tmp_path))
    records = collect_versions(["other"], [path], dist=["sid"])
    assert [r["package"] for r in records] == ["other"]


def test_collect_versions_missing_file_raises(tmp_path):
    missing = os.path.join(str(tmp_path), "does-not-exist.json")
    try:
        collect_versions(["libtest"], [missing])
    except FileNotFoundError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("expected FileNotFoundError")
