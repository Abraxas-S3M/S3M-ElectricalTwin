"""Tests for topology models: unknown switch state, cycles, and JSON round-trip."""

from __future__ import annotations

from datetime import UTC, date, datetime

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
    SourceNode,
    SourceType,
    SwitchState,
    TopologySnapshot,
)


def _node(node_id: str, asset_type: AssetType = AssetType.BUSBAR) -> ElectricalNode:
    return ElectricalNode(
        id=node_id,
        name=f"node-{node_id}",
        asset_type=asset_type,
        nominal_voltage_v=480.0,
        phases=3,
        parent_facility_id="fac-1",
        criticality=Criticality.HIGH,
        provenance=Provenance(source=ProvenanceSource.SYNTHETIC),
    )


def test_node_with_unknown_state_edges_validates():
    node = _node("n1")
    edge = ElectricalEdge(
        id="e1",
        from_node_id="n1",
        to_node_id="n2",
        edge_kind=EdgeKind.FEEDER,
        switch_state=SwitchState.UNKNOWN,
    )
    assert edge.switch_state is SwitchState.UNKNOWN
    # An edge left at its default state is also UNKNOWN.
    default_edge = ElectricalEdge(
        id="e2",
        from_node_id="n1",
        to_node_id="n3",
        edge_kind=EdgeKind.TIE,
    )
    assert default_edge.switch_state is SwitchState.UNKNOWN
    assert node.id == "n1"


def test_topology_expresses_cycles_via_tie_breaker():
    # Two buses fed from a common source, joined by a closed tie -> a genuine
    # cycle. The model must accept this; it is not a tree.
    nodes = [_node("busA"), _node("busB"), _node("tie", AssetType.TIE_BREAKER)]
    edges = [
        ElectricalEdge(
            id="fA",
            from_node_id="busA",
            to_node_id="busB",
            edge_kind=EdgeKind.FEEDER,
            switch_state=SwitchState.CLOSED,
        ),
        ElectricalEdge(
            id="tieAB",
            from_node_id="busB",
            to_node_id="busA",
            edge_kind=EdgeKind.TIE,
            switch_state=SwitchState.CLOSED,
            switching_device_node_id="tie",
        ),
    ]
    snap = TopologySnapshot(
        snapshot_id="snap-1",
        facility_id="fac-1",
        captured_at=datetime(2026, 1, 1, tzinfo=UTC),
        nodes=nodes,
        edges=edges,
        sources=[SourceNode(node_id="busA", source_type=SourceType.UTILITY, priority=0)],
    )
    # from/to pairs form a directed cycle busA -> busB -> busA.
    pairs = {(e.from_node_id, e.to_node_id) for e in snap.edges}
    assert ("busA", "busB") in pairs and ("busB", "busA") in pairs


def test_topology_snapshot_round_trips_through_json():
    node = _node("xfmr", AssetType.TRANSFORMER)
    node.rated = RatedData(
        kva=Provenanced(value=1500.0, provenance=Provenance(source=ProvenanceSource.NAMEPLATE)),
        impedance_percent=Provenanced(value=5.75),
        commissioned_on=Provenanced(value=date(2020, 6, 1)),
        manufacturer=Provenanced(value="synthetic-oem"),
    )
    snap = TopologySnapshot(
        snapshot_id="snap-json",
        facility_id="fac-1",
        captured_at=datetime(2026, 2, 3, 4, 5, 6, tzinfo=UTC),
        nodes=[node],
        edges=[
            ElectricalEdge(
                id="e-src",
                from_node_id="grid",
                to_node_id="xfmr",
                edge_kind=EdgeKind.SOURCE_CONNECTION,
                switch_state=SwitchState.CLOSED,
                impedance=EdgeImpedance(r_ohm=0.01, x_ohm=0.05, length_m=12.5),
                ampacity_a=2000.0,
            )
        ],
        sources=[
            SourceNode(
                node_id="grid",
                source_type=SourceType.UTILITY,
                rated_kva=2500.0,
                priority=0,
            )
        ],
    )

    as_json = snap.model_dump_json()
    restored = TopologySnapshot.model_validate_json(as_json)

    assert restored == snap
    assert restored.nodes[0].rated.kva.value == 1500.0
    assert restored.nodes[0].rated.kva.provenance.source is ProvenanceSource.NAMEPLATE
    assert restored.nodes[0].rated.commissioned_on.value == date(2020, 6, 1)
    assert restored.edges[0].impedance.length_m == 12.5


def test_facility_frequency_is_configurable():
    assert Facility(id="f", name="default").nominal_frequency_hz == 60.0
    assert Facility(id="f", name="eu", nominal_frequency_hz=50.0).nominal_frequency_hz == 50.0
