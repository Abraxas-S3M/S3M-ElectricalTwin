"""Synthetic reference facility FAC-001, plus topology and telemetry.

This package brings together three cooperating pieces, all fully synthetic and
advisory/observe-only (nothing here is a setpoint, command, or control action):

* **Asset inventory (WP1.1)** -- FAC-001, a synthetic mid-size manufacturing
  plant with hospital-grade backup, defined as JSON under
  :mod:`packages.reference_facility.data` and validated into the canonical
  electrical model by :func:`load_reference_facility`. It carries a *deliberate*
  sub-metering gap on the ``MCC-003`` branch that must not be "fixed".
* **Driver-based telemetry (WP1.3)** -- a code-defined single-line
  (:mod:`packages.reference_facility.facility`) driven by explicit load drivers
  to produce deterministic synthetic telemetry (:func:`generate`), and projected
  onto the canonical :class:`~packages.canonical_electrical_model.TopologySnapshot`
  by :func:`topology_snapshot`.
* **FAC-001 switching variants (WP1.2)** -- named switching states of the WP1.1
  inventory, with series impedances populated for power flow, in
  :mod:`packages.reference_facility.switching`.

FAC-001 is **not** based on, derived from, or a model of any real facility,
site, customer, partner, or vendor; every value is invented for testing and is
labelled ``DataProvenance.SYNTHETIC``.
"""

from __future__ import annotations

from .channels import CHANNEL_UNITS, Channel
from .facility import (
    VARIANTS,
    FacilityNode,
    FacilitySource,
    NodeRole,
    reference_facility,
)
from .loader import load_reference_facility
from .models import MeteringPlan, ReferenceFacility, SubMeter
from .telemetry import TelemetryReading, generate
from .topology import topology_snapshot

__all__ = [
    # WP1.1 asset inventory
    "load_reference_facility",
    "ReferenceFacility",
    "MeteringPlan",
    "SubMeter",
    # WP1.3 single-line + driver-based telemetry
    "CHANNEL_UNITS",
    "Channel",
    "VARIANTS",
    "FacilityNode",
    "FacilitySource",
    "NodeRole",
    "reference_facility",
    "TelemetryReading",
    "generate",
    "topology_snapshot",
]
