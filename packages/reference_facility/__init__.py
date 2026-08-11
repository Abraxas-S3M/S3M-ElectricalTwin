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
"""Synthetic reference facility FAC-001.

FAC-001 is a **synthetic** mid-size manufacturing plant with hospital-grade
backup. It exists so every later analytic work package has a realistic, fixed
asset inventory to run against. **It is NOT based on, derived from, or a model
of any real facility, site, customer, partner, or vendor** -- every value is
invented for testing and is labelled ``DataProvenance.SYNTHETIC``.

The facility is defined as JSON under :mod:`packages.reference_facility.data`
and validated into the canonical electrical model at load time via
:func:`load_reference_facility`.

The inventory contains a *deliberate* sub-metering gap on the MCC-003 branch
(utilities and HVAC): it is a test fixture for the Work Package 3 unmetered-load
detector and must not be "fixed" (see ``data/metering.json``).
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
from .loader import load_reference_facility
from .models import MeteringPlan, ReferenceFacility, SubMeter

__all__ = [
    "load_reference_facility",
    "ReferenceFacility",
    "MeteringPlan",
    "SubMeter",
]
