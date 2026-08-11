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
"""

from __future__ import annotations

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
