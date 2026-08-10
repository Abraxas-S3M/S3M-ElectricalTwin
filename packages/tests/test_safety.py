"""Tests for the hard platform safety invariant.

These assert the read-only posture of S3M ElectricalTwin: the control-write
flag is disabled and the read-only guard does not raise under normal
conditions. The guard's failure path is also exercised by forcing the flag
truthy, which tests are explicitly permitted to do.
"""

from __future__ import annotations

import pytest
from canonical_electrical_model import safety
from canonical_electrical_model.safety import CONTROL_WRITE_ENABLED, assert_read_only


def test_control_write_enabled_is_false() -> None:
    assert CONTROL_WRITE_ENABLED is False
    assert safety.CONTROL_WRITE_ENABLED is False


def test_assert_read_only_does_not_raise() -> None:
    assert assert_read_only() is None


def test_assert_read_only_raises_when_flag_truthy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(safety, "CONTROL_WRITE_ENABLED", True)
    with pytest.raises(RuntimeError):
        assert_read_only()
