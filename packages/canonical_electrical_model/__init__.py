"""Canonical electrical model for S3M ElectricalTwin (advisory, read-only)."""

from canonical_electrical_model.safety import (
    CONTROL_WRITE_ENABLED,
    assert_read_only,
)

__all__ = ["CONTROL_WRITE_ENABLED", "assert_read_only"]
