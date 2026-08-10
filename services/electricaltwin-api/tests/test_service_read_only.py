"""Smoke tests for the read-only posture of the API service package."""

from __future__ import annotations

import app
from canonical_electrical_model import assert_read_only


def test_app_package_imports() -> None:
    """The API service package imports cleanly."""
    assert app.__doc__ is not None


def test_service_is_read_only() -> None:
    """The read-only invariant holds from the service perspective."""
    assert_read_only()
