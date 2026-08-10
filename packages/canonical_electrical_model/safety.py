"""Hard platform safety invariant for S3M ElectricalTwin.

This module encodes a **hard platform invariant**: no code path anywhere in
this repository may write to, command or actuate any control system, PLC,
breaker, drive, relay or field device. S3M ElectricalTwin is an advisory,
read-only digital twin — it observes, models and analyses; it never controls.

A control tier, were one ever to exist, would be a **separately authorised and
safety-certified product** with its own governance, review and certification
lifecycle. It would never be this product, and it would never live behind the
flag below. :data:`CONTROL_WRITE_ENABLED` exists solely to make the invariant
explicit and machine-checkable, and is permanently ``False`` here.
"""

from __future__ import annotations

CONTROL_WRITE_ENABLED: bool = False
"""Permanently ``False``. No control-write path may exist in this repository."""


def assert_read_only() -> None:
    """Fail loudly if the read-only invariant has been violated.

    Raises:
        RuntimeError: if :data:`CONTROL_WRITE_ENABLED` is truthy, which would
            indicate that a control-write capability has been introduced in
            violation of the hard platform invariant.
    """
    if CONTROL_WRITE_ENABLED:
        raise RuntimeError(
            "Safety invariant violated: CONTROL_WRITE_ENABLED is truthy. "
            "S3M ElectricalTwin is advisory and read-only; no code path may "
            "write to, command or actuate any control system or field device."
        )
