"""Tests for the FAC-001 reference facility and its topology variants.

These exercise the energization solver against *real* facility data (not the
hand-built unit fixtures in ``test_engineering_topology.py``):

* every variant loads and solves;
* ``base`` produces two electrically separate LV islands;
* ``utility_loss`` produces both ENERGIZED_BACKUP and ENERGIZED_UPS;
* ``unknown_switch`` produces at least one INDETERMINATE node and *zero*
  guessed energization states;
* ``tie_closed`` forms a cycle that terminates;
* a node fed through ``ATS-001`` is flagged ``is_backfed`` because its edge is
  traversed against the declared direction.
"""

from __future__ import annotations

import pytest

from packages.canonical_electrical_model import (
    EnergizationState,
    SwitchState,
    TopologySnapshot,
)
from packages.electrical_engineering import ENERGIZED_STATES
from packages.electrical_engineering.topology import solve_energization
from packages.reference_facility import (
    VARIANTS,
    closed_graph_has_cycle,
    count_lv_islands,
    facility_header,
    load_reference_facility,
    lv_island_of,
    topology_snapshot,
)

#: Island-B nodes reachable only through the TX-002 LV main (``E-TX2``).
_ISLAND_B_BEHIND_TX2 = {
    "SWGR-LV-002",
    "PNL-B-001",
    "MTR-B-001",
    "UPS-IN-001",
}


def _solve(variant: str):
    snapshot = topology_snapshot(variant)
    return snapshot, solve_energization(
        snapshot.nodes, snapshot.edges, snapshot.sources
    )


def _edge_by_id(snapshot: TopologySnapshot, edge_id: str):
    return next(e for e in snapshot.edges if e.id == edge_id)


def test_load_reference_facility_present() -> None:
    snapshot = load_reference_facility()
    assert isinstance(snapshot, TopologySnapshot)
    assert snapshot.facility_id == "FAC-001"
    assert len(snapshot.nodes) == 16
    assert {"UTIL-001", "GEN-001", "UPS-001"} <= {s.node_id for s in snapshot.sources}


def test_facility_header() -> None:
    header = facility_header()
    assert header.id == "FAC-001"
    assert 480.0 in header.nominal_voltage_levels
    assert 13_800.0 in header.nominal_voltage_levels
    assert header.nominal_frequency_hz == 60.0


def test_every_variant_loads_and_solves() -> None:
    for variant in VARIANTS:
        snapshot, result = _solve(variant)
        node_ids = {n.id for n in snapshot.nodes}
        # Every declared node resolves to some state.
        assert node_ids <= set(result)
        assert all(r.state in set(EnergizationState) for r in result.values())


def test_variants_share_identical_nodes_and_impedances() -> None:
    # Only switch states change between variants; the physical network (nodes
    # and edge impedances) is invariant. This is what WP2's power flow relies on.
    base = topology_snapshot("base")
    base_nodes = {n.id: n for n in base.nodes}
    base_imp = {e.id: e.impedance for e in base.edges}
    for variant in VARIANTS:
        snapshot = topology_snapshot(variant)
        assert {n.id: n for n in snapshot.nodes} == base_nodes
        assert {e.id: e.impedance for e in snapshot.edges} == base_imp


def test_every_edge_has_series_impedance() -> None:
    # WP2 power flow needs r/x on every conductor; assert none are missing.
    snapshot = load_reference_facility()
    for edge in snapshot.edges:
        assert edge.impedance is not None, edge.id
        assert edge.impedance.r_ohm is not None, edge.id
        assert edge.impedance.x_ohm is not None, edge.id


def test_transformers_carry_rated_impedance() -> None:
    snapshot = load_reference_facility()
    by_id = {n.id: n for n in snapshot.nodes}
    for tx in ("TX-001", "TX-002"):
        rated = by_id[tx].rated
        assert rated is not None
        assert rated.impedance_percent is not None
        assert rated.impedance_percent.value == pytest.approx(5.75)
        assert rated.kva is not None


def test_sources_are_priority_ordered() -> None:
    snapshot = load_reference_facility()
    priority = {s.node_id: s.priority for s in snapshot.sources}
    assert priority["UTIL-001"] < priority["GEN-001"] < priority["UPS-001"]


def test_edges_reference_existing_nodes() -> None:
    snapshot = load_reference_facility()
    node_ids = {n.id for n in snapshot.nodes}
    for edge in snapshot.edges:
        assert edge.from_node_id in node_ids, edge.id
        assert edge.to_node_id in node_ids, edge.id


def test_base_tie_is_open() -> None:
    snapshot = topology_snapshot("base")
    for tie_edge in ("E-TIE-1", "E-TIE-2"):
        assert _edge_by_id(snapshot, tie_edge).switch_state is SwitchState.OPEN


def test_base_has_two_separate_lv_islands() -> None:
    snapshot = topology_snapshot("base")
    assert count_lv_islands(snapshot) == 2
    island_a = lv_island_of(snapshot, "SWGR-LV-001")
    island_b = lv_island_of(snapshot, "SWGR-LV-002")
    assert "SWGR-LV-002" not in island_a
    assert "SWGR-LV-001" not in island_b
    assert island_a.isdisjoint(island_b)


def test_base_islands_both_energized_from_utility() -> None:
    _snapshot, result = _solve("base")
    assert result["SWGR-LV-001"].state is EnergizationState.ENERGIZED_PRIMARY
    assert result["SWGR-LV-002"].state is EnergizationState.ENERGIZED_PRIMARY
    # Independent supply paths: neither LV bus is fed via the other.
    assert "SWGR-LV-002" not in result["SWGR-LV-001"].path
    assert "SWGR-LV-001" not in result["SWGR-LV-002"].path


def test_base_has_no_backfeed() -> None:
    _snapshot, result = _solve("base")
    assert all(not r.is_backfed for r in result.values())


def test_tie_closed_merges_into_one_island() -> None:
    snapshot = topology_snapshot("tie_closed")
    assert count_lv_islands(snapshot) == 1
    assert lv_island_of(snapshot, "SWGR-LV-001") == lv_island_of(
        snapshot, "SWGR-LV-002"
    )


def test_tie_closed_forms_a_cycle_that_terminates() -> None:
    snapshot, result = _solve("tie_closed")
    # Closing the tie closes a real electrical loop (through both transformers
    # and the shared MV bus).
    assert closed_graph_has_cycle(snapshot) is True
    assert closed_graph_has_cycle(topology_snapshot("base")) is False
    # The solver terminates and no reconstructed path revisits a node.
    for node_id in ("SWGR-LV-001", "SWGR-LV-002", "CB-TIE-001"):
        res = result[node_id]
        assert res.state in ENERGIZED_STATES
        assert len(res.path) == len(set(res.path))


def test_tx1_out_isolates_transformer_and_transfers_load() -> None:
    snapshot, result = _solve("tx1_out")
    # TX-001 is racked out on both sides.
    assert _edge_by_id(snapshot, "E-TX1").switch_state is SwitchState.RACKED_OUT
    assert _edge_by_id(snapshot, "E-MV-TX1").switch_state is SwitchState.RACKED_OUT
    assert result["TX-001"].state is EnergizationState.DE_ENERGIZED
    # Island A is still energized -- transferred through the closed bus tie.
    assert result["SWGR-LV-001"].state in ENERGIZED_STATES
    assert "CB-TIE-001" in result["SWGR-LV-001"].path


def test_utility_loss_produces_backup_and_ups() -> None:
    _snapshot, result = _solve("utility_loss")
    states = {r.state for r in result.values()}
    assert EnergizationState.ENERGIZED_BACKUP in states
    assert EnergizationState.ENERGIZED_UPS in states
    assert EnergizationState.ENERGIZED_PRIMARY not in states


def test_utility_loss_deenergizes_utility_node() -> None:
    snapshot, result = _solve("utility_loss")
    assert result["UTIL-001"].state is EnergizationState.DE_ENERGIZED
    assert "UTIL-001" not in {s.node_id for s in snapshot.sources}


def test_utility_loss_island_a_backup_not_backfed() -> None:
    # The generator feeds island A the normal way round: energized, not backfed.
    _snapshot, result = _solve("utility_loss")
    for node_id in ("SWGR-LV-001", "PNL-A-001", "MTR-A-001"):
        assert result[node_id].state is EnergizationState.ENERGIZED_BACKUP
        assert result[node_id].is_backfed is False


def test_ats_provides_alternate_backfed_path_to_swgr_lv_002() -> None:
    # ATS-001 creates an alternate source path INTO SWGR-LV-002; because the
    # edge is declared out of the bus, feeding the bus through it is a backfeed.
    _snapshot, result = _solve("utility_loss")
    res = result["SWGR-LV-002"]
    assert res.state is EnergizationState.ENERGIZED_BACKUP
    assert res.is_backfed is True
    assert "ATS-001" in res.path
    assert res.source_node_id == "GEN-001"


def test_ats_edge_is_traversed_against_declared_direction() -> None:
    snapshot, result = _solve("utility_loss")
    ats_out = _edge_by_id(snapshot, "E-ATS-OUT")
    # Declared bus -> ATS ...
    assert ats_out.from_node_id == "SWGR-LV-002"
    assert ats_out.to_node_id == "ATS-001"
    # ... but energization reaches the bus by coming from the ATS (reverse).
    path = result["SWGR-LV-002"].path
    ats_index = path.index("ATS-001")
    assert path[ats_index + 1] == "SWGR-LV-002"


def test_backfed_loads_downstream_of_ats_are_flagged() -> None:
    _snapshot, result = _solve("utility_loss")
    for node_id in ("PNL-B-001", "MTR-B-001", "UPS-IN-001"):
        assert result[node_id].is_backfed is True


def test_unknown_switch_variant_has_an_unknown_edge() -> None:
    snapshot = topology_snapshot("unknown_switch")
    unknown_edges = [
        e for e in snapshot.edges if e.switch_state is SwitchState.UNKNOWN
    ]
    assert len(unknown_edges) >= 1
    assert any(e.id == "E-TX2" for e in unknown_edges)


def test_unknown_switch_yields_indeterminate_without_guessing() -> None:
    _snapshot, result = _solve("unknown_switch")
    indeterminate = {
        node_id
        for node_id, r in result.items()
        if r.state is EnergizationState.INDETERMINATE
    }
    # At least one INDETERMINATE node...
    assert len(indeterminate) >= 1
    # ... and it is precisely the island reachable only through the UNKNOWN
    # switch -- proving no guess was made in either direction.
    assert indeterminate == _ISLAND_B_BEHIND_TX2
    for node_id in _ISLAND_B_BEHIND_TX2:
        state = result[node_id].state
        assert state is EnergizationState.INDETERMINATE
        assert state not in ENERGIZED_STATES
        assert state is not EnergizationState.DE_ENERGIZED
        assert result[node_id].indeterminate_reason is not None


def test_unknown_switch_leaves_healthy_island_a_definite() -> None:
    # The UNKNOWN switch on island B must not blind island A: it stays a
    # definite ENERGIZED_PRIMARY, never contaminated to INDETERMINATE.
    _snapshot, result = _solve("unknown_switch")
    for node_id in ("SWGR-LV-001", "PNL-A-001", "MTR-A-001"):
        assert result[node_id].state is EnergizationState.ENERGIZED_PRIMARY


def test_critical_panel_is_ups_backed_in_every_variant() -> None:
    # The double-conversion UPS decouples its output from its input, so the
    # critical panel is UPS-sourced regardless of the upstream switching state.
    for variant in VARIANTS:
        _snapshot, result = _solve(variant)
        assert (
            result["PNL-CRIT-001"].state is EnergizationState.ENERGIZED_UPS
        ), variant


def test_topology_snapshot_is_deterministic() -> None:
    first = topology_snapshot("base")
    second = topology_snapshot("base")
    assert first.model_dump() == second.model_dump()
    assert first.captured_at == second.captured_at


def test_building_a_variant_does_not_mutate_the_base() -> None:
    base_before = topology_snapshot("base")
    states_before = {e.id: e.switch_state for e in base_before.edges}
    # Build other variants (which override switch states)...
    topology_snapshot("tie_closed")
    topology_snapshot("utility_loss")
    base_after = topology_snapshot("base")
    states_after = {e.id: e.switch_state for e in base_after.edges}
    assert states_before == states_after


def test_unknown_variant_name_raises() -> None:
    with pytest.raises(ValueError):
        topology_snapshot("does-not-exist")
