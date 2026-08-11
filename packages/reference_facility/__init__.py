"""S3M ElectricalTwin -- reference facility package.

A single, fully synthetic reference facility (``FAC-001``) built from the
canonical electrical model, together with named switching *variants* of its
topology. This is the shared fixture the energization solver and (later) the
power-flow engine reason over.

The public surface is intentionally small:

* :func:`load_reference_facility` -- FAC-001 as a base :class:`TopologySnapshot`.
* :func:`topology_snapshot` -- FAC-001 with a named switching variant applied.
* :func:`facility_header` -- the FAC-001 :class:`Facility` site metadata.
* graph helpers :func:`lv_islands`, :func:`count_lv_islands`,
  :func:`lv_island_of` and :func:`closed_graph_has_cycle`.

All data is synthetic. Nothing here carries a setpoint, command or control
action; edge switch states are *observed* positions only.
"""

from __future__ import annotations

from packages.canonical_electrical_model import TopologySnapshot

from .analysis import (
    closed_graph_has_cycle,
    count_lv_islands,
    lv_island_of,
    lv_islands,
)
from .facility import (
    CAPTURED_AT,
    FACILITY_ID,
    LV_VOLTAGE_V,
    MV_VOLTAGE_V,
    base_snapshot,
    build_edges,
    build_nodes,
    build_sources,
    facility_header,
    load_reference_facility,
)
from .variants import VARIANTS, topology_snapshot

__all__ = [
    "TopologySnapshot",
    "FACILITY_ID",
    "CAPTURED_AT",
    "MV_VOLTAGE_V",
    "LV_VOLTAGE_V",
    "load_reference_facility",
    "facility_header",
    "base_snapshot",
    "build_nodes",
    "build_edges",
    "build_sources",
    "topology_snapshot",
    "VARIANTS",
    "lv_islands",
    "count_lv_islands",
    "lv_island_of",
    "closed_graph_has_cycle",
]
