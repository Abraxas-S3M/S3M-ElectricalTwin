"""Tests for the reference-facility topology projection and facility spec."""

from __future__ import annotations

from packages.canonical_electrical_model import (
    EdgeKind,
    ProvenanceSource,
    SourceType,
    SwitchState,
)
from packages.reference_facility import (
    NodeRole,
    reference_facility,
    topology_snapshot,
)


def test_topology_snapshot_base_has_expected_core_nodes():
    snap = topology_snapshot("base")
    ids = {n.id for n in snap.nodes}
    for expected in ("UTIL-001", "TX-001", "MSB-001", "MCC-001", "PP-001", "PV-001"):
        assert expected in ids


def test_topology_snapshot_edges_reference_known_nodes():
    snap = topology_snapshot("base")
    ids = {n.id for n in snap.nodes}
    assert snap.edges
    for edge in snap.edges:
        assert edge.from_node_id in ids
        assert edge.to_node_id in ids


def test_topology_base_feeder_edges_form_a_spanning_tree():
    snap = topology_snapshot("base")
    feeder_edges = [e for e in snap.edges if e.edge_kind is not EdgeKind.TIE]
    # A radial tree over N nodes has exactly N-1 parent edges.
    assert len(feeder_edges) == len(snap.nodes) - 1
    children = [e.to_node_id for e in feeder_edges]
    assert len(children) == len(set(children))  # each node has one parent


def test_gen_backup_variant_adds_generator_source():
    base = topology_snapshot("base")
    gen = topology_snapshot("gen_backup")
    base_sources = {s.source_type for s in base.sources}
    gen_sources = {s.source_type for s in gen.sources}
    assert SourceType.GENERATOR not in base_sources
    assert SourceType.GENERATOR in gen_sources


def test_tie_alt_variant_adds_open_tie_edge():
    snap = topology_snapshot("tie_alt")
    ties = [e for e in snap.edges if e.edge_kind is EdgeKind.TIE]
    assert len(ties) == 1
    assert ties[0].switch_state is SwitchState.OPEN


def test_unknown_variant_falls_back_to_base():
    unknown = topology_snapshot("does-not-exist")
    base = topology_snapshot("base")
    assert [n.id for n in unknown.nodes] == [n.id for n in base.nodes]
    assert len(unknown.edges) == len(base.edges)


def test_topology_snapshot_is_deterministic():
    a = topology_snapshot("base")
    b = topology_snapshot("base")
    assert a.model_dump() == b.model_dump()


def test_all_nodes_carry_synthetic_provenance():
    snap = topology_snapshot("base")
    for node in snap.nodes:
        assert node.provenance.source is ProvenanceSource.SYNTHETIC


def test_facility_children_ordering_is_stable():
    fac = reference_facility("base")
    children = [c.node_id for c in fac.children_of("MCC-001")]
    assert children == ["MTR-001", "MTR-002", "MTR-003"]


def test_metered_balance_groups_have_complete_children():
    fac = reference_facility("base")
    groups = dict(fac.metered_balance_groups())
    assert set(groups["MSB-001"]) == {"MCC-001", "PP-001", "CAP-001", "PV-001"}
    assert set(groups["PP-001"]) == {"LIGHT-001", "HVAC-001", "PLUG-001"}
    assert groups["TX-001"] == ("MSB-001",)


def test_pv_and_capacitor_roles_present():
    fac = reference_facility("base")
    roles = {n.node_id: n.role for n in fac.nodes}
    assert roles["PV-001"] is NodeRole.SOLAR_PV
    assert roles["CAP-001"] is NodeRole.CAPACITOR_BANK
