"""Network integration tests for the metadata tools.

These tests talk to a real Debian mirror and download metadata, so they are
opt-in: set ``WANNA_DEBIAN_RUN_INTEGRATION=1`` to run them.  They are also
marked ``integration`` so they can be selected/deselected explicitly.
"""

import os

import pytest

from wanna_debian_mcp import tools

DEBIAN_BASE_URL = "http://deb.debian.org/debian/"

_RUN = os.environ.get("WANNA_DEBIAN_RUN_INTEGRATION") == "1"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _RUN,
        reason="set WANNA_DEBIAN_RUN_INTEGRATION=1 to run network integration tests",
    ),
]


def test_list_distributions_integration():
    result = tools.list_distributions(DEBIAN_BASE_URL)
    assert "trixie" in result["distributions"]


def test_update_metadata_and_search_integration(tmp_path):
    metadata_dir = str(tmp_path)
    result = tools.update_metadata(
        DEBIAN_BASE_URL,
        metadata_dir=metadata_dir,
        dist=["trixie"],
        comp=["main"],
        build=["source"],
        force=True,
    )
    assert result["updated"] is True
    assert os.path.exists(os.path.join(metadata_dir, "config.json"))

    found = tools.search_packages(
        ["bash"], metadata_dir=metadata_dir, dist=["trixie"]
    )
    assert found["count"] >= 1
    assert any(record["package"] == "bash" for record in found["records"])
