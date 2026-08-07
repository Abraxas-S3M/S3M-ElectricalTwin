"""Tests for the hard read-only safety invariant of S3M ElectricalTwin."""

from __future__ import annotations

from canonical_electrical_model import safety
from canonical_electrical_model.safety import (
    CONTROL_WRITE_ENABLED,
    assert_read_only,
)


def test_control_write_enabled_is_false() -> None:
    """The control-write flag must be permanently disabled."""
    assert CONTROL_WRITE_ENABLED is False
    assert safety.CONTROL_WRITE_ENABLED is False


def test_assert_read_only_does_not_raise() -> None:
    """With the invariant intact, ``assert_read_only`` returns without error."""
    assert_read_only()
