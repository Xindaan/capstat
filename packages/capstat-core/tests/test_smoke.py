"""Smoke test: the package imports and exposes a version string.

Real statistical coverage arrives with the Tier-1 methods (see TASK.md). This
test only guards the bootstrap wiring.
"""

from __future__ import annotations

import capstat_core


def test_version_is_exposed() -> None:
    assert isinstance(capstat_core.__version__, str)
    assert capstat_core.__version__.count(".") == 2
