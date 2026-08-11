"""The synthetic reference facility: metadata, asset inventory and base graph.

This module defines a single, fixed, entirely **synthetic** facility used to
demonstrate the platform end to end. Nothing here describes a real site, a real
customer, or a real product; every asset, rating and identifier is invented for
demonstration and is safe to publish.

The facility is a medium mixed-use building served from a single medium-voltage
utility service, with a standby generator, a dual-bus 480 V main switchboard
joined by a normally-open tie, two step-down transformers feeding 208 V
distribution panels, and a UPS carrying a life-safety critical panel. This shape
is deliberately rich enough to exercise primary/backup/UPS energization, an open
tie, backfeed through a closed tie, and ``UNKNOWN`` switch handling.

The base graph is expressed with the canonical :mod:`canonical_electrical_model`
types so it can be served directly by the read-only API. Topology *variants*
(see :mod:`reference_facility.topology`) are derived from this base by overriding
switch states only; the node and edge inventory never changes between variants.
"""The reference facility — a synthetic single-line diagram used as the fixed
substrate for every seeded scenario.

This module is deliberately self-contained: it declares the full node
inventory, the metered parent/child power hierarchy used by the power-balance
checks, and the simulation timebase shared by the scenario catalogue and the
telemetry generator. Everything here is synthetic; no real site, customer, or
product is represented.

The node identifiers (``TX-001``, ``M-003``, ``MCC-003`` ...) are the stable
handles the scenario ground truth refers to. The power hierarchy encodes which
feeder meters *should* sum to which parent-feed meter, which is exactly the
relationship the unmetered-load scenario (SC-08) violates.
"""Reference-facility electrical model (single-line + engineering parameters).

This module defines the *synthetic* reference facility that the telemetry
generator drives. It is a generic hot-climate light-industrial site fed from a
single medium-voltage utility service through a step-down transformer to a
480 V main switchboard. No real site, city, or country is named; every value
here is synthetic and for modelling only.

The model is a **radial tree** rooted at the utility service. Each node records
the resistance/reactance of the feeder connecting it to its parent so that the
telemetry generator can model cable losses and enforce a parent-child power
balance (parent power == sum of children + modelled losses). The tree shape and
the per-node driver coefficients are the sole source of truth shared by
:mod:`packages.reference_facility.topology` (which projects it onto the canonical
:class:`~packages.canonical_electrical_model.TopologySnapshot`) and
:mod:`packages.reference_facility.telemetry` (which generates readings).

Nothing in this module is a setpoint, command, or control action: it is a
static description of rated reality only.
"""

from __future__ import annotations

from packages.canonical_electrical_model import (
    AssetType,
    Criticality,
    EdgeKind,
    ElectricalEdge,
    ElectricalNode,
    Facility,
    Location,
    Provenance,
    ProvenanceSource,
    SectorProfile,
    SourceNode,
    SourceType,
    SwitchState,
)

#: Stable identifier for the one reference facility.
FACILITY_ID = "REF-FAC-001"

#: A note attached to every served payload, reinforcing that this is synthetic
#: demonstration data and any analytics derived from it are preliminary.
SYNTHETIC_NOTICE = (
    "All data for the reference facility is synthetic and invented for "
    "demonstration; it describes no real site or customer. Any analytics are "
    "preliminary and advisory only."
)

_SYNTHETIC_PROVENANCE = Provenance(
    source=ProvenanceSource.SYNTHETIC,
    method="reference_facility",
    reference=FACILITY_ID,
)


def _node(
    node_id: str,
    name: str,
    asset_type: AssetType,
    *,
    voltage: float | None,
    phases: int,
    criticality: Criticality | None = None,
    area: str | None = None,
) -> ElectricalNode:
    return ElectricalNode(
        id=node_id,
        name=name,
        asset_type=asset_type,
        nominal_voltage_v=voltage,
        phases=phases,  # type: ignore[arg-type]
        parent_facility_id=FACILITY_ID,
        criticality=criticality,
        location=Location(site="Reference Facility", area=area) if area else None,
        provenance=_SYNTHETIC_PROVENANCE,
    )


def _edge(
    edge_id: str,
    from_node_id: str,
    to_node_id: str,
    edge_kind: EdgeKind,
    switch_state: SwitchState,
    *,
    ampacity_a: float | None = None,
    switching_device_node_id: str | None = None,
) -> ElectricalEdge:
    return ElectricalEdge(
        id=edge_id,
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        edge_kind=edge_kind,
        switch_state=switch_state,
        switching_device_node_id=switching_device_node_id,
        ampacity_a=ampacity_a,
        provenance=_SYNTHETIC_PROVENANCE,
    )


# --- Base asset inventory ---------------------------------------------------

_BASE_NODES: tuple[ElectricalNode, ...] = (
    _node("UTIL-1", "Utility service", AssetType.UTILITY_SERVICE,
          voltage=13_800.0, phases=3, area="Service entrance"),
    _node("GEN-1", "Standby generator", AssetType.GENERATOR,
          voltage=480.0, phases=3, criticality=Criticality.HIGH, area="Generator yard"),
    _node("MV-XFMR", "Main step-down transformer", AssetType.TRANSFORMER,
          voltage=480.0, phases=3, criticality=Criticality.HIGH, area="Vault"),
    _node("MSB", "Main switchboard", AssetType.SWITCHBOARD,
          voltage=480.0, phases=3, criticality=Criticality.CRITICAL, area="Electrical room"),
    _node("BUS-A", "Distribution bus A", AssetType.BUS,
          voltage=480.0, phases=3, criticality=Criticality.HIGH, area="Electrical room"),
    _node("BUS-B", "Distribution bus B", AssetType.BUS,
          voltage=480.0, phases=3, criticality=Criticality.HIGH, area="Electrical room"),
    _node("XFMR-A", "Distribution transformer A", AssetType.TRANSFORMER,
          voltage=208.0, phases=3, criticality=Criticality.MEDIUM, area="Electrical room"),
    _node("XFMR-B", "Distribution transformer B", AssetType.TRANSFORMER,
          voltage=208.0, phases=3, criticality=Criticality.MEDIUM, area="Electrical room"),
    _node("PANEL-A", "Distribution panel A", AssetType.PANELBOARD,
          voltage=208.0, phases=3, criticality=Criticality.MEDIUM, area="Level 1"),
    _node("PANEL-B", "Distribution panel B", AssetType.PANELBOARD,
          voltage=208.0, phases=3, criticality=Criticality.MEDIUM, area="Level 2"),
    _node("UPS-1", "Uninterruptible power supply", AssetType.UPS,
          voltage=208.0, phases=3, criticality=Criticality.CRITICAL, area="Electrical room"),
    _node("PANEL-CRIT", "Life-safety panel", AssetType.PANELBOARD,
          voltage=208.0, phases=3, criticality=Criticality.LIFE_SAFETY, area="Level 1"),
    _node("LOAD-A1", "General load A1", AssetType.LOAD,
          voltage=208.0, phases=3, criticality=Criticality.LOW, area="Level 1"),
    _node("LOAD-A2", "General load A2", AssetType.LOAD,
          voltage=208.0, phases=3, criticality=Criticality.MEDIUM, area="Level 1"),
    _node("LOAD-B1", "General load B1", AssetType.LOAD,
          voltage=208.0, phases=3, criticality=Criticality.LOW, area="Level 2"),
    _node("LOAD-B2", "General load B2", AssetType.LOAD,
          voltage=208.0, phases=3, criticality=Criticality.MEDIUM, area="Level 2"),
    _node("LOAD-CRIT1", "Life-safety load", AssetType.LOAD,
          voltage=208.0, phases=3, criticality=Criticality.LIFE_SAFETY, area="Level 1"),
)

# --- Base edges (declared switch states describe the NORMAL configuration) --

_BASE_EDGES: tuple[ElectricalEdge, ...] = (
    _edge("E-UTIL-XFMR", "UTIL-1", "MV-XFMR", EdgeKind.SOURCE_CONNECTION,
          SwitchState.CLOSED, ampacity_a=1200.0),
    _edge("E-XFMR-MSB", "MV-XFMR", "MSB", EdgeKind.TRANSFORMER_WINDING,
          SwitchState.CLOSED, ampacity_a=2500.0),
    _edge("E-GEN-MSB", "GEN-1", "MSB", EdgeKind.SOURCE_CONNECTION,
          SwitchState.OPEN, ampacity_a=1600.0),
    _edge("E-MSB-BUSA", "MSB", "BUS-A", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=1600.0),
    _edge("E-MSB-BUSB", "MSB", "BUS-B", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=1600.0),
    _edge("E-TIE-AB", "BUS-A", "BUS-B", EdgeKind.TIE,
          SwitchState.OPEN, ampacity_a=1600.0),
    _edge("E-BUSA-XFMRA", "BUS-A", "XFMR-A", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=800.0),
    _edge("E-XFMRA-PANELA", "XFMR-A", "PANEL-A", EdgeKind.TRANSFORMER_WINDING,
          SwitchState.CLOSED, ampacity_a=800.0),
    _edge("E-BUSB-XFMRB", "BUS-B", "XFMR-B", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=800.0),
    _edge("E-XFMRB-PANELB", "XFMR-B", "PANEL-B", EdgeKind.TRANSFORMER_WINDING,
          SwitchState.CLOSED, ampacity_a=800.0),
    _edge("E-BUSA-UPS", "BUS-A", "UPS-1", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=400.0),
    _edge("E-UPS-CRIT", "UPS-1", "PANEL-CRIT", EdgeKind.SOURCE_CONNECTION,
          SwitchState.CLOSED, ampacity_a=400.0),
    _edge("E-PANELA-A1", "PANEL-A", "LOAD-A1", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=200.0),
    _edge("E-PANELA-A2", "PANEL-A", "LOAD-A2", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=200.0),
    _edge("E-PANELB-B1", "PANEL-B", "LOAD-B1", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=200.0),
    _edge("E-PANELB-B2", "PANEL-B", "LOAD-B2", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=200.0),
    _edge("E-PANELCRIT-C1", "PANEL-CRIT", "LOAD-CRIT1", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=200.0),
)

_BASE_SOURCES: tuple[SourceNode, ...] = (
    SourceNode(node_id="UTIL-1", source_type=SourceType.UTILITY, rated_kva=2500.0, priority=0),
    SourceNode(node_id="GEN-1", source_type=SourceType.GENERATOR, rated_kva=1250.0, priority=1),
    # The UPS is a standby island source: it is normally fed through, so it must
    # rank below the utility and the generator. If both are lost, it becomes the
    # only source and carries the critical panel.
    SourceNode(node_id="UPS-1", source_type=SourceType.UPS, rated_kva=300.0, priority=2),
)


def facility() -> Facility:
    """Return the metadata for the reference facility (a fresh instance)."""

    return Facility(
        id=FACILITY_ID,
        name="S3M Reference Facility (synthetic)",
        nominal_frequency_hz=60.0,
        nominal_voltage_levels=[13_800.0, 480.0, 208.0],
        timezone="UTC",
        sector_profile=SectorProfile.MIXED_USE,
    )


def base_nodes() -> list[ElectricalNode]:
    """Return the full asset inventory (a fresh list of fresh instances)."""

    return [n.model_copy(deep=True) for n in _BASE_NODES]


def base_edges() -> list[ElectricalEdge]:
    """Return the base edges in their NORMAL switch configuration."""

    return [e.model_copy(deep=True) for e in _BASE_EDGES]


def base_sources() -> list[SourceNode]:
    """Return the energization sources for the facility."""

    return [s.model_copy(deep=True) for s in _BASE_SOURCES]
from datetime import UTC, datetime, timedelta

from packages.canonical_electrical_model.enums import (
    AssetType,
    Criticality,
    EdgeKind,
    SourceType,
    SwitchState,
)
from packages.canonical_electrical_model.topology import (
    ElectricalEdge,
    ElectricalNode,
    Facility,
    SourceNode,
    TopologySnapshot,
)

FACILITY_ID = "REF-FACILITY-001"
FACILITY_NAME = "S3M Reference Facility"

# --- Simulation timebase -------------------------------------------------
# The whole scenario suite runs on one fixed, deterministic clock so that a
# scenario's ``onset_at`` maps to an exact sample index in the telemetry
# generator. Daily cadence over one quarter is long enough to express the
# multi-week degradations (rotor-bar sidebands, meter drift) while staying
# cheap to generate.
SIM_START: datetime = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
SIM_STEP: timedelta = timedelta(days=1)
SIM_STEPS: int = 90


def sim_timestamp(index: int) -> datetime:
    """Return the wall-clock timestamp of sample ``index`` (0-based)."""

    return SIM_START + index * SIM_STEP


def sim_index(moment: datetime) -> int:
    """Return the 0-based sample index at (or exactly on) ``moment``."""

    delta = moment - SIM_START
    return round(delta / SIM_STEP)


# --- Node inventory ------------------------------------------------------
# Each entry: id -> (display name, asset type, nominal voltage V, phases,
# criticality). Assets without a dedicated ``AssetType`` member (variable
# frequency drives, the UPS battery string, the transfer switch) use the
# closest canonical member plus a descriptive name.
_NODE_SPECS: tuple[
    tuple[str, str, AssetType, float, int, Criticality], ...
] = (
    ("UTIL-001", "Utility Service Entrance",
     AssetType.UTILITY_SERVICE, 13800.0, 3, Criticality.CRITICAL),
    ("GEN-001", "Standby Diesel Generator",
     AssetType.GENERATOR, 480.0, 3, Criticality.CRITICAL),
    ("UPS-001", "Static Double-Conversion UPS",
     AssetType.UPS, 480.0, 3, Criticality.CRITICAL),
    ("BATT-001", "UPS Battery String",
     AssetType.OTHER, 480.0, 1, Criticality.CRITICAL),
    ("ATS-001", "Automatic Transfer Switch",
     AssetType.TIE_BREAKER, 480.0, 3, Criticality.CRITICAL),
    ("TX-001", "Main Transformer 13.8kV/480V",
     AssetType.TRANSFORMER, 480.0, 3, Criticality.CRITICAL),
    ("SWGR-LV-001", "LV Switchgear Bus 1",
     AssetType.SWITCHGEAR, 480.0, 3, Criticality.HIGH),
    ("SWGR-LV-002", "LV Switchgear Bus 2",
     AssetType.SWITCHGEAR, 480.0, 3, Criticality.HIGH),
    ("CAP-001", "Automatic Capacitor Bank",
     AssetType.CAPACITOR_BANK, 480.0, 3, Criticality.MEDIUM),
    ("CB-LV-001", "LV Tie Breaker",
     AssetType.TIE_BREAKER, 480.0, 3, Criticality.HIGH),
    ("CB-LV-002", "LV Feeder Breaker to MCC-001",
     AssetType.BREAKER, 480.0, 3, Criticality.MEDIUM),
    ("CB-LV-003", "LV Feeder Breaker to MCC-002",
     AssetType.BREAKER, 480.0, 3, Criticality.MEDIUM),
    ("CB-LV-004", "LV Feeder Breaker to MCC-003",
     AssetType.BREAKER, 480.0, 3, Criticality.MEDIUM),
    ("CB-LV-005", "LV Feeder Breaker to Panel LV-005",
     AssetType.BREAKER, 480.0, 3, Criticality.MEDIUM),
    ("MCC-001", "Motor Control Center 1",
     AssetType.SWITCHBOARD, 480.0, 3, Criticality.MEDIUM),
    ("MCC-002", "Motor Control Center 2",
     AssetType.SWITCHBOARD, 480.0, 3, Criticality.MEDIUM),
    ("MCC-003", "Motor Control Center 3",
     AssetType.SWITCHBOARD, 480.0, 3, Criticality.MEDIUM),
    ("MTR-MCC-001", "MCC-1 Feeder Revenue Meter",
     AssetType.METER, 480.0, 3, Criticality.LOW),
    ("MTR-MCC-002", "MCC-2 Feeder Revenue Meter",
     AssetType.METER, 480.0, 3, Criticality.LOW),
    ("MTR-MCC-003", "MCC-3 Feeder Revenue Meter",
     AssetType.METER, 480.0, 3, Criticality.LOW),
    ("M-001", "Cooling Tower Pump Motor",
     AssetType.MOTOR, 480.0, 3, Criticality.MEDIUM),
    ("M-002", "Boiler Feedwater Pump Motor",
     AssetType.MOTOR, 480.0, 3, Criticality.MEDIUM),
    ("M-003", "Process Exhaust Fan Motor",
     AssetType.MOTOR, 480.0, 3, Criticality.MEDIUM),
    ("VFD-001", "VFD — Air Handler 1",
     AssetType.OTHER, 480.0, 3, Criticality.MEDIUM),
    ("VFD-002", "VFD — Air Handler 2",
     AssetType.OTHER, 480.0, 3, Criticality.MEDIUM),
    ("CH-001", "Centrifugal Chiller",
     AssetType.LOAD, 480.0, 3, Criticality.HIGH),
    ("LOAD-MCC-003-A", "MCC-3 Process Load A",
     AssetType.LOAD, 480.0, 3, Criticality.MEDIUM),
    ("PNL-LV-005", "Panelboard downstream of CB-LV-005",
     AssetType.PANELBOARD, 480.0, 3, Criticality.LOW),
    ("LOAD-LV-005", "Lighting/Receptacle Load on PNL-LV-005",
     AssetType.LOAD, 480.0, 3, Criticality.LOW),
)


def _build_nodes() -> tuple[ElectricalNode, ...]:
    return tuple(
        ElectricalNode(
            id=node_id,
            name=name,
            asset_type=asset_type,
            nominal_voltage_v=voltage,
            phases=phases,  # type: ignore[arg-type]
            parent_facility_id=FACILITY_ID,
            criticality=criticality,
        )
        for (node_id, name, asset_type, voltage, phases, criticality) in _NODE_SPECS
    )


# --- Edges (single-line connectivity) ------------------------------------
# ``switching_device_node_id`` points a feeder edge at the breaker whose live
# position governs it. This is what makes SC-09 expressible: CB-LV-005 can
# report CLOSED while the through-current it governs is zero.
_EDGE_SPECS: tuple[
    tuple[str, str, str, EdgeKind, SwitchState, str | None], ...
] = (
    ("E-UTIL-TX", "UTIL-001", "TX-001", EdgeKind.TRANSFORMER_WINDING, SwitchState.CLOSED, None),
    ("E-TX-ATS", "TX-001", "ATS-001", EdgeKind.FEEDER, SwitchState.CLOSED, None),
    ("E-GEN-ATS", "GEN-001", "ATS-001", EdgeKind.SOURCE_CONNECTION, SwitchState.OPEN, None),
    ("E-ATS-SWGR1", "ATS-001", "SWGR-LV-001", EdgeKind.FEEDER, SwitchState.CLOSED, None),
    ("E-SWGR1-UPS", "SWGR-LV-001", "UPS-001", EdgeKind.FEEDER, SwitchState.CLOSED, None),
    ("E-BATT-UPS", "BATT-001", "UPS-001", EdgeKind.SOURCE_CONNECTION, SwitchState.CLOSED, None),
    ("E-SWGR1-SWGR2", "SWGR-LV-001", "SWGR-LV-002",
     EdgeKind.TIE, SwitchState.CLOSED, "CB-LV-001"),
    ("E-SWGR1-CB005", "SWGR-LV-001", "PNL-LV-005",
     EdgeKind.FEEDER, SwitchState.CLOSED, "CB-LV-005"),
    ("E-CB005-LOAD", "PNL-LV-005", "LOAD-LV-005", EdgeKind.FEEDER, SwitchState.CLOSED, None),
    ("E-SWGR2-CAP", "SWGR-LV-002", "CAP-001", EdgeKind.FEEDER, SwitchState.CLOSED, None),
    ("E-SWGR2-MCC1", "SWGR-LV-002", "MCC-001", EdgeKind.FEEDER, SwitchState.CLOSED, "CB-LV-002"),
    ("E-SWGR2-MCC2", "SWGR-LV-002", "MCC-002", EdgeKind.FEEDER, SwitchState.CLOSED, "CB-LV-003"),
    ("E-SWGR2-MCC3", "SWGR-LV-002", "MCC-003", EdgeKind.FEEDER, SwitchState.CLOSED, "CB-LV-004"),
    ("E-MCC1-MTR", "MCC-001", "MTR-MCC-001", EdgeKind.FEEDER, SwitchState.CLOSED, None),
    ("E-MCC2-MTR", "MCC-002", "MTR-MCC-002", EdgeKind.FEEDER, SwitchState.CLOSED, None),
    ("E-MCC3-MTR", "MCC-003", "MTR-MCC-003", EdgeKind.FEEDER, SwitchState.CLOSED, None),
    ("E-MCC1-M1", "MCC-001", "M-001", EdgeKind.FEEDER, SwitchState.CLOSED, None),
    ("E-MCC1-VFD1", "MCC-001", "VFD-001", EdgeKind.FEEDER, SwitchState.CLOSED, None),
    ("E-MCC2-M2", "MCC-002", "M-002", EdgeKind.FEEDER, SwitchState.CLOSED, None),
    ("E-MCC2-CH1", "MCC-002", "CH-001", EdgeKind.FEEDER, SwitchState.CLOSED, None),
    ("E-MCC3-M3", "MCC-003", "M-003", EdgeKind.FEEDER, SwitchState.CLOSED, None),
    ("E-MCC3-LOADA", "MCC-003", "LOAD-MCC-003-A", EdgeKind.FEEDER, SwitchState.CLOSED, None),
    ("E-SWGR2-VFD2", "SWGR-LV-002", "VFD-002", EdgeKind.FEEDER, SwitchState.CLOSED, None),
)


def _build_edges() -> tuple[ElectricalEdge, ...]:
    return tuple(
        ElectricalEdge(
            id=edge_id,
            from_node_id=from_id,
            to_node_id=to_id,
            edge_kind=kind,
            switch_state=state,
            switching_device_node_id=device,
        )
        for (edge_id, from_id, to_id, kind, state, device) in _EDGE_SPECS
    )


def _build_sources() -> tuple[SourceNode, ...]:
    return (
        SourceNode(
            node_id="UTIL-001", source_type=SourceType.UTILITY,
            rated_kva=2500.0, priority=0,
        ),
        SourceNode(
            node_id="GEN-001", source_type=SourceType.GENERATOR,
            rated_kva=750.0, priority=1,
        ),
        SourceNode(
            node_id="UPS-001", source_type=SourceType.UPS,
            rated_kva=300.0, priority=2,
        ),
        SourceNode(
            node_id="BATT-001", source_type=SourceType.BATTERY,
            rated_kva=300.0, priority=3,
        ),
    )


# --- Metered power hierarchy --------------------------------------------
# parent feeder -> metered children whose real power must sum to the parent's
# measured throughput. These are the boundaries the power-balance guard walks.
POWER_HIERARCHY: dict[str, tuple[str, ...]] = {
    "SWGR-LV-002": ("MCC-001", "MCC-002", "MCC-003"),
    "MCC-001": ("M-001", "VFD-001"),
    "MCC-002": ("M-002", "CH-001"),
    "MCC-003": ("M-003", "LOAD-MCC-003-A"),
}

# Baseline real power (kW) drawn by each leaf load. Parent feeds are derived
# bottom-up as the sum of their children (plus any injected unmetered load).
BASE_LOAD_KW: dict[str, float] = {
    "M-001": 55.0,
    "VFD-001": 30.0,
    "M-002": 45.0,
    "CH-001": 120.0,
    "M-003": 37.0,
    "LOAD-MCC-003-A": 22.0,
}


def metered_parents() -> tuple[str, ...]:
    """Return the parent nodes whose child meters must sum to their feed."""

    return tuple(POWER_HIERARCHY.keys())


def leaf_load_ids() -> tuple[str, ...]:
    """Return the metered leaf loads at the bottom of the power hierarchy."""

    return tuple(BASE_LOAD_KW.keys())


def reference_facility() -> Facility:
    """Return the synthetic :class:`Facility` header for the reference site."""

    return Facility(
        id=FACILITY_ID,
        name=FACILITY_NAME,
        nominal_frequency_hz=60.0,
        nominal_voltage_levels=[13800.0, 480.0],
        timezone="UTC",
    )


def reference_topology() -> TopologySnapshot:
    """Return an immutable topology snapshot of the reference facility."""

    return TopologySnapshot(
        snapshot_id="REF-SNAPSHOT-001",
        facility_id=FACILITY_ID,
        captured_at=SIM_START,
        nodes=list(_build_nodes()),
        edges=list(_build_edges()),
        sources=list(_build_sources()),
    )


def facility_node_ids() -> frozenset[str]:
    """Return the set of every node id present in the reference facility."""

    return frozenset(spec[0] for spec in _NODE_SPECS)


def node_exists(node_id: str) -> bool:
    """Return ``True`` when ``node_id`` names a node in the facility."""

    return node_id in facility_node_ids()


__all__ = [
    "FACILITY_ID",
    "FACILITY_NAME",
    "SIM_START",
    "SIM_STEP",
    "SIM_STEPS",
    "sim_timestamp",
    "sim_index",
    "POWER_HIERARCHY",
    "BASE_LOAD_KW",
    "metered_parents",
    "leaf_load_ids",
    "reference_facility",
    "reference_topology",
    "facility_node_ids",
    "node_exists",
]
from dataclasses import dataclass, field
from enum import Enum

from packages.canonical_electrical_model import AssetType, SourceType

LV_VOLTAGE_V: float = 480.0
"""Nominal line-to-line voltage of the low-voltage network (V)."""

MV_VOLTAGE_V: float = 13800.0
"""Nominal line-to-line voltage of the medium-voltage service (V)."""

NOMINAL_FREQUENCY_HZ: float = 60.0
"""Nominal system frequency (Hz) for the target market."""


class NodeRole(str, Enum):
    """Electrical role a node plays in the generation model.

    The role selects which driver equations and telemetry channels apply. It is
    an internal modelling concept and is distinct from the canonical
    :class:`~packages.canonical_electrical_model.AssetType`.
    """

    SOURCE = "SOURCE"
    TRANSFORMER = "TRANSFORMER"
    BUS = "BUS"
    VFD_LOAD = "VFD_LOAD"
    LOAD = "LOAD"
    SOLAR_PV = "SOLAR_PV"
    CAPACITOR_BANK = "CAPACITOR_BANK"


@dataclass(frozen=True)
class FacilityNode:
    """One node of the reference facility plus its engineering parameters.

    All power figures are in kilowatts / kilovars; impedances in ohms; voltages
    in volts. Fields default to neutral values so a node only sets what applies
    to its :class:`NodeRole`.
    """

    node_id: str
    name: str
    role: NodeRole
    asset_type: AssetType
    nominal_v_ll: float
    parent_id: str | None = None
    feeder_r_ohm: float = 0.0
    feeder_x_ohm: float = 0.0
    rated_kva: float = 0.0

    # Additive load drivers (see telemetry.P_node): base + shift + thermal + occ.
    base_kw: float = 0.0
    production_coefficient_kw: float = 0.0
    thermal_coefficient_kw: float = 0.0
    occupancy_coefficient_kw: float = 0.0
    load_power_factor: float = 0.90
    rated_kw: float = 0.0

    # Transformer loss model: no_load_loss_kw + load_loss_kw * loading**2.
    no_load_loss_kw: float = 0.0
    load_loss_kw: float = 0.0

    # Solar inverter nameplate (kW of DC-derived AC capacity at clear-sky peak).
    pv_capacity_kw: float = 0.0

    # Capacitor bank: kvar per switchable stage and the number of stages.
    cap_stage_kvar: float = 0.0
    cap_max_stages: int = 0


@dataclass(frozen=True)
class FacilitySource:
    """A supply source attached to a node."""

    node_id: str
    source_type: SourceType
    priority: int
    rated_kva: float


@dataclass(frozen=True)
class ReferenceFacility:
    """The complete reference facility for one topology variant."""

    facility_id: str
    variant: str
    nodes: tuple[FacilityNode, ...]
    sources: tuple[FacilitySource, ...]
    tie_edges: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def node(self, node_id: str) -> FacilityNode:
        for candidate in self.nodes:
            if candidate.node_id == node_id:
                return candidate
        raise KeyError(node_id)

    def children_of(self, node_id: str) -> tuple[FacilityNode, ...]:
        """Child nodes of ``node_id`` in stable declaration order."""
        return tuple(n for n in self.nodes if n.parent_id == node_id)

    def metered_balance_groups(self) -> tuple[tuple[str, tuple[str, ...]], ...]:
        """Parent -> children groups that must satisfy a power balance.

        Only buses/transformers with *complete* child metering are returned, so
        a caller can verify ``P_parent == sum(P_children) + losses`` at each.
        """
        groups: list[tuple[str, tuple[str, ...]]] = []
        for node in self.nodes:
            if node.role in (NodeRole.BUS, NodeRole.TRANSFORMER):
                children = self.children_of(node.node_id)
                if children:
                    groups.append(
                        (node.node_id, tuple(c.node_id for c in children))
                    )
        return tuple(groups)


def _base_nodes() -> list[FacilityNode]:
    """The shared node set common to every variant, in stable order."""

    return [
        FacilityNode(
            node_id="UTIL-001",
            name="Utility service",
            role=NodeRole.SOURCE,
            asset_type=AssetType.UTILITY_SERVICE,
            nominal_v_ll=MV_VOLTAGE_V,
            parent_id=None,
            rated_kva=4000.0,
        ),
        FacilityNode(
            node_id="TX-001",
            name="Main transformer 13.8kV/480V",
            role=NodeRole.TRANSFORMER,
            asset_type=AssetType.TRANSFORMER,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="UTIL-001",
            rated_kva=2500.0,
            no_load_loss_kw=3.1,
            load_loss_kw=21.0,
        ),
        FacilityNode(
            node_id="MSB-001",
            name="Main 480V switchboard",
            role=NodeRole.BUS,
            asset_type=AssetType.SWITCHGEAR,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="TX-001",
            feeder_r_ohm=0.0009,
            feeder_x_ohm=0.0006,
        ),
        FacilityNode(
            node_id="MCC-001",
            name="Motor control centre",
            role=NodeRole.BUS,
            asset_type=AssetType.SWITCHBOARD,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="MSB-001",
            feeder_r_ohm=0.0080,
            feeder_x_ohm=0.0050,
        ),
        FacilityNode(
            node_id="PP-001",
            name="Distribution panelboard",
            role=NodeRole.BUS,
            asset_type=AssetType.PANELBOARD,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="MSB-001",
            feeder_r_ohm=0.0120,
            feeder_x_ohm=0.0070,
        ),
        FacilityNode(
            node_id="CAP-001",
            name="Power-factor correction capacitor bank",
            role=NodeRole.CAPACITOR_BANK,
            asset_type=AssetType.CAPACITOR_BANK,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="MSB-001",
            feeder_r_ohm=0.0100,
            feeder_x_ohm=0.0060,
            cap_stage_kvar=50.0,
            cap_max_stages=4,
        ),
        FacilityNode(
            node_id="PV-001",
            name="Rooftop solar PV inverter",
            role=NodeRole.SOLAR_PV,
            asset_type=AssetType.OTHER,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="MSB-001",
            feeder_r_ohm=0.0100,
            feeder_x_ohm=0.0060,
            pv_capacity_kw=300.0,
        ),
        FacilityNode(
            node_id="MTR-001",
            name="Process motor A (VFD)",
            role=NodeRole.VFD_LOAD,
            asset_type=AssetType.MOTOR,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="MCC-001",
            feeder_r_ohm=0.0200,
            feeder_x_ohm=0.0120,
            base_kw=120.0,
            production_coefficient_kw=260.0,
            load_power_factor=0.84,
            rated_kw=420.0,
        ),
        FacilityNode(
            node_id="MTR-002",
            name="Process motor B (VFD)",
            role=NodeRole.VFD_LOAD,
            asset_type=AssetType.MOTOR,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="MCC-001",
            feeder_r_ohm=0.0250,
            feeder_x_ohm=0.0150,
            base_kw=90.0,
            production_coefficient_kw=200.0,
            load_power_factor=0.83,
            rated_kw=320.0,
        ),
        FacilityNode(
            node_id="MTR-003",
            name="Process motor C (VFD)",
            role=NodeRole.VFD_LOAD,
            asset_type=AssetType.MOTOR,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="MCC-001",
            feeder_r_ohm=0.0300,
            feeder_x_ohm=0.0180,
            base_kw=60.0,
            production_coefficient_kw=140.0,
            load_power_factor=0.82,
            rated_kw=220.0,
        ),
        FacilityNode(
            node_id="LIGHT-001",
            name="Lighting load",
            role=NodeRole.LOAD,
            asset_type=AssetType.LOAD,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="PP-001",
            feeder_r_ohm=0.0500,
            feeder_x_ohm=0.0250,
            base_kw=15.0,
            occupancy_coefficient_kw=40.0,
            load_power_factor=0.95,
            rated_kw=70.0,
        ),
        FacilityNode(
            node_id="HVAC-001",
            name="HVAC / chiller auxiliary load",
            role=NodeRole.LOAD,
            asset_type=AssetType.LOAD,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="PP-001",
            feeder_r_ohm=0.0400,
            feeder_x_ohm=0.0220,
            base_kw=40.0,
            thermal_coefficient_kw=120.0,
            occupancy_coefficient_kw=30.0,
            load_power_factor=0.88,
            rated_kw=220.0,
        ),
        FacilityNode(
            node_id="PLUG-001",
            name="Small-power / plug load",
            role=NodeRole.LOAD,
            asset_type=AssetType.LOAD,
            nominal_v_ll=LV_VOLTAGE_V,
            parent_id="PP-001",
            feeder_r_ohm=0.0600,
            feeder_x_ohm=0.0300,
            base_kw=20.0,
            occupancy_coefficient_kw=35.0,
            load_power_factor=0.90,
            rated_kw=70.0,
        ),
    ]


def reference_facility(variant: str = "base") -> ReferenceFacility:
    """Return the reference facility for a topology ``variant``.

    Variants share the same node set and driver coefficients and differ only in
    their supply arrangement / tie configuration:

    * ``base`` -- single utility service, no tie.
    * ``gen_backup`` -- adds a standby diesel generator source at ``MSB-001``.
    * ``tie_alt`` -- adds a (normally-open) tie between ``MCC-001`` and
      ``PP-001`` recording an alternate feed path.

    Any unrecognised variant falls back to ``base``.
    """

    resolved_variant = variant if variant in ("base", "gen_backup", "tie_alt") else "base"

    nodes = tuple(_base_nodes())
    sources: list[FacilitySource] = [
        FacilitySource(
            node_id="UTIL-001",
            source_type=SourceType.UTILITY,
            priority=0,
            rated_kva=4000.0,
        )
    ]
    tie_edges: tuple[tuple[str, str], ...] = ()

    if resolved_variant == "gen_backup":
        sources.append(
            FacilitySource(
                node_id="MSB-001",
                source_type=SourceType.GENERATOR,
                priority=1,
                rated_kva=1500.0,
            )
        )
    elif resolved_variant == "tie_alt":
        tie_edges = (("MCC-001", "PP-001"),)

    return ReferenceFacility(
        facility_id="FAC-REF-001",
        variant=resolved_variant,
        nodes=nodes,
        sources=tuple(sources),
        tie_edges=tie_edges,
    )


VARIANTS: tuple[str, ...] = ("base", "gen_backup", "tie_alt")
"""The topology variants understood by :func:`reference_facility`."""
