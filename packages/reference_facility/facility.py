"""FAC-001 -- the canonical reference facility.

This module builds a single, fully synthetic reference facility (``FAC-001``)
from the canonical electrical model. It is the shared fixture the rest of the
system reasons over: the topology variants in :mod:`variants`, the energization
solver in :mod:`packages.electrical_engineering.topology`, and (in later work
packages) the power-flow engine all consume this one facility.

Design of FAC-001
-----------------
A small but realistic double-ended substation feeding two independent 480 V
switchgear lineups::

                         UTIL-001  (utility, priority 0)
                            |  E-UTIL
                      SWGR-MV-001  (13.8 kV switchgear)
                        /            \\
                  E-MV-TX1          E-MV-TX2
                     |                  |
                  TX-001             TX-002        (13.8 kV / 480 V)
                     |  E-TX1           |  E-TX2
              SWGR-LV-001  ---( CB-TIE-001 )---  SWGR-LV-002
             (island A, 480V)   E-TIE-1/2       (island B, 480V)
              /        \\                          /   |   \\   \\
        PNL-A-001   MTR-A-001            PNL-B-001 MTR-B-001 UPS-IN-001
                                                            |
                                    (UPS-001 output island) |
                                          UPS-001 --E-UPS-OUT--> PNL-CRIT-001

Backup supplies:

* ``GEN-001`` (generator, priority 1) connects to island A directly
  (``E-GEN``) and, through the automatic transfer switch ``ATS-001``, provides
  an *alternate source path to* ``SWGR-LV-002`` (``E-ATS-GEN`` +
  ``E-ATS-OUT``). ``E-ATS-OUT`` is declared *out of* the bus
  (``SWGR-LV-002 -> ATS-001``), so when the generator energizes the bus through
  it the flow is against the declared direction -- a genuine backfeed the
  solver must flag.
* ``UPS-001`` (UPS, priority 2) feeds only the critical panel
  ``PNL-CRIT-001``. The UPS is modelled as two nodes -- an input (``UPS-IN-001``,
  a monitored load on island B) and an output (``UPS-001``, a source) -- with
  **no** conducting edge between them, because a double-conversion UPS decouples
  its output from its input. This is what keeps ``PNL-CRIT-001`` sourced by the
  UPS in every variant rather than being back-claimed by an upstream supply.

Base switching state
--------------------
``CB-TIE-001`` is **open** (two independent LV islands), the generator breaker
and the ATS are open (backup idle), and the utility feeds both transformers.

All data here is synthetic. Nothing in this module is a setpoint, command or
control action; switch states are *observed* positions only.
"""

from __future__ import annotations

from datetime import UTC, datetime

from packages.canonical_electrical_model import (
    AssetType,
    Criticality,
    EdgeImpedance,
    EdgeKind,
    ElectricalEdge,
    ElectricalNode,
    Facility,
    Provenance,
    Provenanced,
    ProvenanceSource,
    RatedData,
    SectorProfile,
    SourceNode,
    SourceType,
    SwitchState,
    TopologySnapshot,
)

FACILITY_ID = "FAC-001"

#: Voltage levels present in FAC-001 (volts).
MV_VOLTAGE_V = 13_800.0
LV_VOLTAGE_V = 480.0

#: A fixed, deterministic capture time. The reference facility is a static
#: fixture, so its snapshot timestamp must never depend on wall-clock time.
CAPTURED_AT = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

_SYNTHETIC = Provenance(
    source=ProvenanceSource.SYNTHETIC,
    method="reference_facility.FAC-001",
    reference="synthetic reference facility",
)


def _p(value: float | str | int) -> Provenanced:
    """Wrap a synthetic nameplate value with its provenance label."""

    return Provenanced(value=value, provenance=_SYNTHETIC)


def _imp(
    r_ohm: float,
    x_ohm: float,
    length_m: float | None = None,
) -> EdgeImpedance:
    return EdgeImpedance(r_ohm=r_ohm, x_ohm=x_ohm, length_m=length_m)


def _node(
    node_id: str,
    name: str,
    asset_type: AssetType,
    nominal_voltage_v: float,
    *,
    criticality: Criticality | None = None,
    rated: RatedData | None = None,
) -> ElectricalNode:
    return ElectricalNode(
        id=node_id,
        name=name,
        asset_type=asset_type,
        nominal_voltage_v=nominal_voltage_v,
        phases=3,
        parent_facility_id=FACILITY_ID,
        criticality=criticality,
        rated=rated,
        provenance=_SYNTHETIC,
    )


def _edge(
    edge_id: str,
    from_node_id: str,
    to_node_id: str,
    edge_kind: EdgeKind,
    switch_state: SwitchState,
    impedance: EdgeImpedance,
    *,
    switching_device_node_id: str | None = None,
    ampacity_a: float | None = None,
) -> ElectricalEdge:
    return ElectricalEdge(
        id=edge_id,
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        edge_kind=edge_kind,
        switch_state=switch_state,
        switching_device_node_id=switching_device_node_id,
        impedance=impedance,
        ampacity_a=ampacity_a,
        provenance=_SYNTHETIC,
    )


def build_nodes() -> list[ElectricalNode]:
    """Every node in FAC-001, with rated data populated for power flow."""

    transformer_rated = RatedData(
        voltage_v=_p(LV_VOLTAGE_V),
        kva=_p(1500.0),
        impedance_percent=_p(5.75),
        vector_group=_p("Dyn11"),
        frequency_hz=_p(60.0),
    )
    return [
        _node(
            "UTIL-001",
            "Utility service entrance",
            AssetType.UTILITY_SERVICE,
            MV_VOLTAGE_V,
            rated=RatedData(voltage_v=_p(MV_VOLTAGE_V), kva=_p(2500.0)),
        ),
        _node(
            "SWGR-MV-001",
            "Medium-voltage switchgear",
            AssetType.SWITCHGEAR,
            MV_VOLTAGE_V,
        ),
        _node(
            "TX-001",
            "Transformer TX-001 (13.8kV/480V)",
            AssetType.TRANSFORMER,
            MV_VOLTAGE_V,
            rated=transformer_rated,
        ),
        _node(
            "TX-002",
            "Transformer TX-002 (13.8kV/480V)",
            AssetType.TRANSFORMER,
            MV_VOLTAGE_V,
            rated=transformer_rated,
        ),
        _node(
            "SWGR-LV-001",
            "Low-voltage switchgear (island A)",
            AssetType.SWITCHGEAR,
            LV_VOLTAGE_V,
        ),
        _node(
            "SWGR-LV-002",
            "Low-voltage switchgear (island B)",
            AssetType.SWITCHGEAR,
            LV_VOLTAGE_V,
        ),
        _node(
            "CB-TIE-001",
            "Bus tie breaker (SWGR-LV-001 <-> SWGR-LV-002)",
            AssetType.TIE_BREAKER,
            LV_VOLTAGE_V,
        ),
        _node(
            "PNL-A-001",
            "Distribution panel (island A)",
            AssetType.PANELBOARD,
            LV_VOLTAGE_V,
            criticality=Criticality.MEDIUM,
        ),
        _node(
            "MTR-A-001",
            "Process motor (island A)",
            AssetType.MOTOR,
            LV_VOLTAGE_V,
            criticality=Criticality.HIGH,
        ),
        _node(
            "PNL-B-001",
            "Distribution panel (island B)",
            AssetType.PANELBOARD,
            LV_VOLTAGE_V,
            criticality=Criticality.MEDIUM,
        ),
        _node(
            "MTR-B-001",
            "Process motor (island B)",
            AssetType.MOTOR,
            LV_VOLTAGE_V,
            criticality=Criticality.HIGH,
        ),
        _node(
            "UPS-IN-001",
            "UPS-001 rectifier input (island B load)",
            AssetType.UPS,
            LV_VOLTAGE_V,
        ),
        _node(
            "UPS-001",
            "UPS-001 inverter output",
            AssetType.UPS,
            LV_VOLTAGE_V,
        ),
        _node(
            "PNL-CRIT-001",
            "Critical distribution panel",
            AssetType.PANELBOARD,
            LV_VOLTAGE_V,
            criticality=Criticality.LIFE_SAFETY,
        ),
        _node(
            "GEN-001",
            "Standby generator",
            AssetType.GENERATOR,
            LV_VOLTAGE_V,
            rated=RatedData(voltage_v=_p(LV_VOLTAGE_V), kva=_p(1500.0)),
        ),
        _node(
            "ATS-001",
            "Automatic transfer switch (alternate feed to SWGR-LV-002)",
            AssetType.DISCONNECT,
            LV_VOLTAGE_V,
        ),
    ]


def build_edges() -> list[ElectricalEdge]:
    """Every edge in FAC-001 in its *base* (normal-operation) switch state.

    Every edge carries a synthetic series impedance so the WP2 power-flow
    engine has a fully populated network. Impedances are small, plausible,
    synthetic values -- not measured or vendor data.
    """

    return [
        _edge(
            "E-UTIL",
            "UTIL-001",
            "SWGR-MV-001",
            EdgeKind.SOURCE_CONNECTION,
            SwitchState.CLOSED,
            _imp(0.030, 0.060, length_m=40.0),
            ampacity_a=1200.0,
        ),
        _edge(
            "E-MV-TX1",
            "SWGR-MV-001",
            "TX-001",
            EdgeKind.FEEDER,
            SwitchState.CLOSED,
            _imp(0.045, 0.075, length_m=35.0),
            ampacity_a=600.0,
        ),
        _edge(
            "E-MV-TX2",
            "SWGR-MV-001",
            "TX-002",
            EdgeKind.FEEDER,
            SwitchState.CLOSED,
            _imp(0.045, 0.075, length_m=35.0),
            ampacity_a=600.0,
        ),
        _edge(
            "E-TX1",
            "TX-001",
            "SWGR-LV-001",
            EdgeKind.TRANSFORMER_WINDING,
            SwitchState.CLOSED,
            _imp(0.0021, 0.0086),
            ampacity_a=1800.0,
        ),
        _edge(
            "E-TX2",
            "TX-002",
            "SWGR-LV-002",
            EdgeKind.TRANSFORMER_WINDING,
            SwitchState.CLOSED,
            _imp(0.0021, 0.0086),
            ampacity_a=1800.0,
        ),
        _edge(
            "E-TIE-1",
            "SWGR-LV-001",
            "CB-TIE-001",
            EdgeKind.TIE,
            SwitchState.OPEN,
            _imp(0.0015, 0.0025, length_m=6.0),
            switching_device_node_id="CB-TIE-001",
            ampacity_a=2000.0,
        ),
        _edge(
            "E-TIE-2",
            "CB-TIE-001",
            "SWGR-LV-002",
            EdgeKind.TIE,
            SwitchState.OPEN,
            _imp(0.0015, 0.0025, length_m=6.0),
            switching_device_node_id="CB-TIE-001",
            ampacity_a=2000.0,
        ),
        _edge(
            "E-A-PNL",
            "SWGR-LV-001",
            "PNL-A-001",
            EdgeKind.FEEDER,
            SwitchState.CLOSED,
            _imp(0.020, 0.012, length_m=30.0),
            ampacity_a=400.0,
        ),
        _edge(
            "E-A-MTR",
            "SWGR-LV-001",
            "MTR-A-001",
            EdgeKind.FEEDER,
            SwitchState.CLOSED,
            _imp(0.028, 0.015, length_m=45.0),
            ampacity_a=250.0,
        ),
        _edge(
            "E-B-PNL",
            "SWGR-LV-002",
            "PNL-B-001",
            EdgeKind.FEEDER,
            SwitchState.CLOSED,
            _imp(0.020, 0.012, length_m=30.0),
            ampacity_a=400.0,
        ),
        _edge(
            "E-B-MTR",
            "SWGR-LV-002",
            "MTR-B-001",
            EdgeKind.FEEDER,
            SwitchState.CLOSED,
            _imp(0.028, 0.015, length_m=45.0),
            ampacity_a=250.0,
        ),
        _edge(
            "E-UPS-IN",
            "SWGR-LV-002",
            "UPS-IN-001",
            EdgeKind.FEEDER,
            SwitchState.CLOSED,
            _imp(0.018, 0.010, length_m=25.0),
            ampacity_a=500.0,
        ),
        _edge(
            "E-UPS-OUT",
            "UPS-001",
            "PNL-CRIT-001",
            EdgeKind.SOURCE_CONNECTION,
            SwitchState.CLOSED,
            _imp(0.015, 0.009, length_m=20.0),
            ampacity_a=500.0,
        ),
        _edge(
            "E-GEN",
            "GEN-001",
            "SWGR-LV-001",
            EdgeKind.SOURCE_CONNECTION,
            SwitchState.OPEN,
            _imp(0.010, 0.012, length_m=15.0),
            ampacity_a=2000.0,
        ),
        _edge(
            "E-ATS-GEN",
            "GEN-001",
            "ATS-001",
            EdgeKind.SOURCE_CONNECTION,
            SwitchState.OPEN,
            _imp(0.010, 0.012, length_m=18.0),
            ampacity_a=1200.0,
        ),
        # Declared *out of* SWGR-LV-002 on purpose: the ATS is drawn on the
        # island-B lineup as a feeder breaker, so the declared direction is
        # bus -> ATS. When the generator energizes the bus through it, the flow
        # is against this declared direction and the solver flags a backfeed.
        _edge(
            "E-ATS-OUT",
            "SWGR-LV-002",
            "ATS-001",
            EdgeKind.TIE,
            SwitchState.OPEN,
            _imp(0.012, 0.010, length_m=22.0),
            switching_device_node_id="ATS-001",
            ampacity_a=1200.0,
        ),
    ]


def build_sources() -> list[SourceNode]:
    """The three supplies of FAC-001, in preference order (lower wins)."""

    return [
        SourceNode(
            node_id="UTIL-001",
            source_type=SourceType.UTILITY,
            rated_kva=2500.0,
            priority=0,
        ),
        SourceNode(
            node_id="GEN-001",
            source_type=SourceType.GENERATOR,
            rated_kva=1500.0,
            priority=1,
        ),
        SourceNode(
            node_id="UPS-001",
            source_type=SourceType.UPS,
            rated_kva=300.0,
            priority=2,
        ),
    ]


def facility_header() -> Facility:
    """The FAC-001 :class:`Facility` header (site metadata)."""

    return Facility(
        id=FACILITY_ID,
        name="S3M Reference Facility FAC-001",
        nominal_frequency_hz=60.0,
        nominal_voltage_levels=[MV_VOLTAGE_V, LV_VOLTAGE_V],
        timezone="UTC",
        sector_profile=SectorProfile.DATA_CENTER,
    )


def base_snapshot() -> TopologySnapshot:
    """The FAC-001 topology in its base (normal-operation) switching state."""

    return TopologySnapshot(
        snapshot_id=f"{FACILITY_ID}-base",
        facility_id=FACILITY_ID,
        captured_at=CAPTURED_AT,
        nodes=build_nodes(),
        edges=build_edges(),
        sources=build_sources(),
    )


def load_reference_facility() -> TopologySnapshot:
    """Load FAC-001 as a topology snapshot in its base switching state.

    Returns the base :class:`TopologySnapshot` (nodes, edges and sources).
    Equivalent to :func:`packages.reference_facility.topology_snapshot` called
    with ``"base"``; provided as the stable entry point for "give me the
    reference facility".
    """

    return base_snapshot()
