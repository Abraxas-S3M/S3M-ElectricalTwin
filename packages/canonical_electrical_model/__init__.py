"""Canonical electrical model: assets, energization state and safety posture.

This package holds the vocabulary the rest of the platform reasons over:

* :mod:`~packages.canonical_electrical_model.safety` — the immutable read-only
  safety posture and the control boundary description.
* :mod:`~packages.canonical_electrical_model.provenance` — the
  :class:`DataProvenance` and :class:`ValidationState` vocabularies.
* :mod:`~packages.canonical_electrical_model.assets` — the canonical electrical
  asset graph and :class:`EnergizationState`.
"""

from packages.canonical_electrical_model.safety import (
    CONTROL_WRITE_ENABLED,
    ControlBoundary,
    assert_read_only,
    control_boundary,
)

__all__ = [
    "CONTROL_WRITE_ENABLED",
    "ControlBoundary",
    "assert_read_only",
    "control_boundary",
]
