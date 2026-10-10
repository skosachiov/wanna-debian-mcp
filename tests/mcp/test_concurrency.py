"""Concurrency and initialization tests for the MCP tool layer (task 4.2)."""

import json
import os
import threading
import time

import apt_pkg

from wanna_debian_mcp import tools


def test_init_apt_is_idempotent():
    tools.init_apt()
    tools.init_apt()
    assert apt_pkg.version_compare("2.0", "1.0") > 0


def _write_metadata(base):
    target = os.path.join(base, "dists", "trixie", "main")
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
            "source": "foo",
            "source_version": "1.0",
        },
        {
            "package": "foo",
            "version": "2.0",
            "dist": "trixie",
            "comp": "main",
            "build": "binary-amd64",
            "arch": "amd64",
            "source": "foo",
            "source_version": "2.0",
        },
    ]
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(records, handle)
    return base


def test_concurrent_searches_are_correct(tmp_path):
    md = _write_metadata(str(tmp_path))
    results = []
    errors = []
    lock = threading.Lock()

    def worker():
        try:
            result = tools.search_packages(["foo"], metadata_dir=md, latest=True)
            with lock:
                results.append(result)
        except Exception as exc:  # pragma: no cover - failure path
            with lock:
                errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    assert len(results) == 8
    assert all(r["count"] == 1 and r["records"][0]["version"] == "2.0" for r in results)


def test_update_metadata_is_serialized(monkeypatch, tmp_path):
    active = 0
    peak = 0
    guard = threading.Lock()

    def fake_update(*args, **kwargs):
        nonlocal active, peak
        with guard:
            active += 1
            peak = max(peak, active)
        time.sleep(0.05)
        with guard:
            active -= 1

    # ``update_metadata`` references the module-global, so patching it here is
    # what the lock is protecting.
    monkeypatch.setattr(tools, "_update_metadata", fake_update)

    def worker(index):
        tools.update_metadata(
            "http://example.invalid/debian/",
            metadata_dir=str(tmp_path / f"md{index}"),
            dist=["trixie"],
            force=True,
        )

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert peak == 1
