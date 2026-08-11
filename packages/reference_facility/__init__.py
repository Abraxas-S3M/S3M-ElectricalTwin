"""Reference facility: synthetic topology and driver-based telemetry.

This package models a single generic hot-climate light-industrial facility for
the S3M ElectricalTwin. It provides:

* :func:`topology_snapshot` -- the facility projected onto the canonical
  :class:`~packages.canonical_electrical_model.TopologySnapshot`;
* :func:`generate` -- deterministic, physically-consistent synthetic telemetry
  driven by explicit load drivers (shift schedule, ambient temperature,
  occupancy, solar irradiance) rather than noise around a mean.

All data produced here is synthetic and advisory/observe-only; nothing in this
package is a setpoint, command, or control action.
"""

from __future__ import annotations

from .channels import CHANNEL_UNITS, Channel
from .facility import (
    VARIANTS,
    FacilityNode,
    FacilitySource,
    NodeRole,
    ReferenceFacility,
    reference_facility,
)
from .telemetry import TelemetryReading, generate
from .topology import topology_snapshot

__all__ = [
    "CHANNEL_UNITS",
    "Channel",
    "VARIANTS",
    "FacilityNode",
    "FacilitySource",
    "NodeRole",
    "ReferenceFacility",
    "reference_facility",
    "TelemetryReading",
    "generate",
    "topology_snapshot",
]
