"""Immutable safety posture for the S3M ElectricalTwin platform.

The platform is *advisory* and *read-only*. It observes, models and reasons; it
never actuates equipment. This module encodes that posture as data and as a
fail-closed startup assertion so that the property is testable and cannot be
turned on by configuration.

The single source of truth is :data:`CONTROL_WRITE_ENABLED`, which is a
``Final`` constant fixed to ``False``. There is deliberately no environment
variable, feature flag or configuration key that can flip it. Any future work
that needs to actuate equipment must go through a separate, independently
reviewed control system that lives outside this platform.
"""Hard platform safety invariant for S3M ElectricalTwin.

This module encodes a **hard platform invariant**: no code path in this
repository may ever write to, command, or actuate any control system, PLC,
breaker, drive, relay, or field device. S3M ElectricalTwin is an advisory,
read-only digital twin. It observes and analyses; it never controls.

A control tier, if one were ever built, would be a **separately authorised and
safety-certified product** with its own governance, review, and certification
lifecycle. It would never be this product, and it would never live behind this
flag. ``CONTROL_WRITE_ENABLED`` therefore exists only to make the invariant
explicit and machine-checkable; it is permanently ``False`` here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

#: Master switch for the control-write path. It is fixed to ``False`` and there
#: is no supported way to set it to ``True``. Enabling equipment actuation is a
#: deliberate architectural decision that must not be reachable from this
#: platform (see ``docs/adr/ADR-0001-advisory-read-only-posture.md``).
CONTROL_WRITE_ENABLED: Final[bool] = False

#: Plain-language advisory statement surfaced to operators and via the API.
ADVISORY_STATEMENT: Final[str] = (
    "This platform is advisory and read-only. It observes and reasons over "
    "electrical system data to produce recommendations for qualified human "
    "operators and licensed engineers. It does not open, close, trip, start, "
    "stop or otherwise actuate any equipment, and it exposes no control-write "
    "path. Every recommendation requires human judgement before any action is "
    "taken, and any protective, calibration, compliance or coordination "
    "outcome remains the deliverable of a licensed engineer."
)

#: Verbs that describe direct actuation of equipment. They are catalogued here
#: so the grounding gate can detect imperative control language that has leaked
#: into a recommendation card.
EQUIPMENT_CONTROL_VERBS: Final[frozenset[str]] = frozenset(
    {
        "open",
        "close",
        "trip",
        "start",
        "stop",
        "set",
        "write",
        "adjust",
    }
)


@dataclass(frozen=True)
class ControlBoundary:
    """Machine-readable description of what the platform will and will not do."""

    control_write_enabled: bool
    posture: str
    advisory_statement: str
    prohibited_actions: tuple[str, ...] = field(default_factory=tuple)
    permitted_actions: tuple[str, ...] = field(default_factory=tuple)


def control_boundary() -> ControlBoundary:
    """Return the current, immutable control boundary description."""

    return ControlBoundary(
        control_write_enabled=CONTROL_WRITE_ENABLED,
        posture="advisory-read-only",
        advisory_statement=ADVISORY_STATEMENT,
        prohibited_actions=(
            "Actuating equipment (open, close, trip, start, stop, set, write, adjust).",
            "Initiating a control-write connection toward operational technology.",
            "Asserting calibration, validation, code-compliance, protection-coordination, "
            "selectivity or arc-flash results.",
        ),
        permitted_actions=(
            "Observing and modelling electrical system data.",
            "Producing grounded, evidence-cited recommendations for humans.",
            "Flagging insufficient data and refusing to answer.",
        ),
    )


class ReadOnlyViolationError(RuntimeError):
    """Raised when the read-only safety invariant is not satisfied."""


def assert_read_only() -> None:
    """Fail closed unless the platform is in its read-only posture.

    This is called at application startup. Because :data:`CONTROL_WRITE_ENABLED`
    is a ``Final`` ``False``, the assertion always holds; the function exists so
    that the invariant is enforced at runtime rather than merely documented, and
    so that any accidental future regression is caught before a service accepts
    traffic.
    """

    if CONTROL_WRITE_ENABLED:
        raise ReadOnlyViolationError(
            "CONTROL_WRITE_ENABLED must be False. This platform is advisory and "
            "read-only and exposes no control-write path."
CONTROL_WRITE_ENABLED: bool = False
"""Permanently ``False``. No control-write path may exist in this repository."""


def assert_read_only() -> None:
    """Fail loudly if the read-only invariant has been violated.

    Raises:
        RuntimeError: if :data:`CONTROL_WRITE_ENABLED` is truthy, indicating
            that a control-write capability has been introduced in violation of
            the hard platform invariant.
    """
    if CONTROL_WRITE_ENABLED:
        raise RuntimeError(
            "Safety invariant violated: CONTROL_WRITE_ENABLED is truthy. "
            "S3M ElectricalTwin is advisory and read-only; no code path may "
            "write to, command, or actuate any control system or field device."
        )
