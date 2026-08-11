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

from .loader import load_reference_facility
from .models import MeteringPlan, ReferenceFacility, SubMeter
from .topology import (
    VARIANTS,
    closed_graph_has_cycle,
    count_lv_islands,
    lv_island_of,
    lv_islands,
    topology_snapshot,
)

__all__ = [
    "load_reference_facility",
    "ReferenceFacility",
    "MeteringPlan",
    "SubMeter",
    # WP1.2 topology snapshots and switching variants
    "topology_snapshot",
    "VARIANTS",
    "lv_islands",
    "count_lv_islands",
    "lv_island_of",
    "closed_graph_has_cycle",
]
