"""Shared pytest configuration.

``apt_pkg`` (from the system ``python3-apt`` package) must be initialized
before any Debian version comparison.  ``predose`` does this at import time,
but tests that only import ``distrotracker`` need it too, so initialize it
once here independently of test collection order.
"""

import apt_pkg

try:
    apt_pkg.init_system()
except Exception:  # pragma: no cover - already initialized / platform specific
    pass
