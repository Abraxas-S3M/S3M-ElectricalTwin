"""Tests for the FAC-001 topology snapshots and switching variants (WP1.2).

These exercise the energization solver against the *real* WP1.1 FAC-001
inventory (not hand-built unit fixtures):

* every variant loads and solves;
* ``base`` produces two electrically separate LV islands;
* ``utility_loss`` produces both ENERGIZED_BACKUP and ENERGIZED_UPS;
* ``unknown_switch`` produces at least one INDETERMINATE node and *zero* guessed
  energization states;
* ``tie_closed`` forms a cycle that terminates;
* a node fed through ``ATS-001`` is flagged ``is_backfed`` because an edge on its
  path is traversed against the declared direction;
* every edge carries a series impedance for WP2 power flow.
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
    load_reference_facility,
    lv_island_of,
    topology_snapshot,
)

#: MCC-003 and everything below it: fed only through the UNKNOWN incomer, with
#: no internal source, so the whole branch must be INDETERMINATE.
_MCC3_BRANCH = {
    "MCC-003",
    "VFD-004",
    "M-007",
    "M-008",
    "CH-001",
    "CH-002",
    "AC-001",
    "P-001",
    "P-002",
    "P-003",
}


def _solve(variant: str):
    snapshot = topology_snapshot(variant)
    return snapshot, solve_energization(
        snapshot.nodes, snapshot.edges, snapshot.sources
    )


def _edge_by_id(snapshot: TopologySnapshot, edge_id: str):
    return next(e for e in snapshot.edges if e.id == edge_id)


def test_precondition_reference_facility_loads() -> None:
    snapshot = load_reference_facility()
    assert len(snapshot.nodes) == 52
    assert snapshot.facility.id == "FAC-001"


def test_variant_names_are_the_five_expected() -> None:
    assert VARIANTS == (
        "base",
        "tie_closed",
        "tx1_out",
        "utility_loss",
        "unknown_switch",
    )


def test_every_variant_loads_and_solves() -> None:
    for variant in VARIANTS:
        snapshot, result = _solve(variant)
        assert isinstance(snapshot, TopologySnapshot)
        assert snapshot.snapshot_id == f"FAC-001-{variant}"
        node_ids = {n.id for n in snapshot.nodes}
        assert node_ids <= set(result)
        assert all(r.state in set(EnergizationState) for r in result.values())


def test_unknown_variant_name_raises() -> None:
    with pytest.raises(ValueError):
        topology_snapshot("does-not-exist")


def test_every_edge_has_series_impedance() -> None:
    # WP2 power flow needs r/x on every conductor.
    snapshot = topology_snapshot("base")
    assert snapshot.edges
    for edge in snapshot.edges:
        assert edge.impedance is not None, edge.id
        assert edge.impedance.r_ohm is not None and edge.impedance.r_ohm > 0.0, edge.id
        assert edge.impedance.x_ohm is not None and edge.impedance.x_ohm > 0.0, edge.id


def test_transformer_winding_impedance_derived_from_rated_percent_z() -> None:
    snapshot = topology_snapshot("base")
    facility = load_reference_facility()
    tx1 = next(n for n in facility.nodes if n.id == "TX-001")
    secondary_v = next(n for n in facility.nodes if n.id == "SWGR-LV-001").nominal_voltage_v
    expected_z = (
        (tx1.rated.impedance_percent.value / 100.0)
        * (secondary_v**2)
        / (tx1.rated.kva.value * 1000.0)
    )
    winding = _edge_by_id(snapshot, "E-TX1-SWGRLV1").impedance
    # Reactive-dominant winding (x >> r) and magnitude tracks the rated %Z.
    assert winding.x_ohm > winding.r_ohm > 0.0
    assert winding.x_ohm == pytest.approx(expected_z * 0.995, abs=1e-6)
    assert winding.length_m is None


def test_physical_network_is_invariant_across_variants() -> None:
    base = topology_snapshot("base")
    base_nodes = {n.id: n for n in base.nodes}
    base_imp = {e.id: e.impedance for e in base.edges}
    for variant in VARIANTS:
        snapshot = topology_snapshot(variant)
        assert {n.id: n for n in snapshot.nodes} == base_nodes
        assert {e.id: e.impedance for e in snapshot.edges} == base_imp


def test_base_bus_tie_is_open() -> None:
    snapshot = topology_snapshot("base")
    assert _edge_by_id(snapshot, "E-TIE").switch_state is SwitchState.OPEN


def test_base_has_two_separate_lv_islands() -> None:
    snapshot = topology_snapshot("base")
    assert count_lv_islands(snapshot) == 2
    island_a = lv_island_of(snapshot, "SWGR-LV-001")
    island_b = lv_island_of(snapshot, "SWGR-LV-002")
    assert "SWGR-LV-002" not in island_a
    assert "SWGR-LV-001" not in island_b
    assert island_a.isdisjoint(island_b)


def test_base_islands_energized_from_utility_and_not_backfed() -> None:
    _snapshot, result = _solve("base")
    for bus in ("SWGR-LV-001", "SWGR-LV-002"):
        assert result[bus].state is EnergizationState.ENERGIZED_PRIMARY
        assert result[bus].is_backfed is False
    # Independent supply paths: neither LV bus is fed via the other.
    assert "SWGR-LV-002" not in result["SWGR-LV-001"].path
    assert "SWGR-LV-001" not in result["SWGR-LV-002"].path


def test_tie_closed_merges_into_one_island() -> None:
    snapshot = topology_snapshot("tie_closed")
    assert count_lv_islands(snapshot) == 1
    assert lv_island_of(snapshot, "SWGR-LV-001") == lv_island_of(
        snapshot, "SWGR-LV-002"
    )


def test_tie_closed_forms_a_cycle_that_terminates() -> None:
    snapshot, result = _solve("tie_closed")
    assert closed_graph_has_cycle(snapshot) is True
    assert closed_graph_has_cycle(topology_snapshot("base")) is False
    # The closed tie edge directly bonds both LV buses (CB-TIE-001 is its
    # switching device, not an on-path node).
    tie = _edge_by_id(snapshot, "E-TIE")
    assert tie.switch_state is SwitchState.CLOSED
    assert tie.switching_device_node_id == "CB-TIE-001"
    for node_id in ("SWGR-LV-001", "SWGR-LV-002"):
        res = result[node_id]
        assert res.state in ENERGIZED_STATES
        # A terminating traversal never revisits a node on the reconstructed path.
        assert len(res.path) == len(set(res.path))


def test_tx1_out_isolates_transformer_and_transfers_load() -> None:
    snapshot, result = _solve("tx1_out")
    assert _edge_by_id(snapshot, "E-TX1-SWGRLV1").switch_state is SwitchState.RACKED_OUT
    assert _edge_by_id(snapshot, "E-SWGRMV-TX1").switch_state is SwitchState.RACKED_OUT
    assert result["TX-001"].state is EnergizationState.DE_ENERGIZED
    # Island A stays energized -- its load is transferred from island B across
    # the closed bus tie, so it is fed via SWGR-LV-002 (a backfeed over the tie).
    assert result["SWGR-LV-001"].state in ENERGIZED_STATES
    assert "SWGR-LV-002" in result["SWGR-LV-001"].path
    assert result["SWGR-LV-001"].is_backfed is True


def test_utility_loss_produces_backup_and_ups() -> None:
    _snapshot, result = _solve("utility_loss")
    states = {r.state for r in result.values()}
    assert EnergizationState.ENERGIZED_BACKUP in states
    assert EnergizationState.ENERGIZED_UPS in states
    assert EnergizationState.ENERGIZED_PRIMARY not in states


def test_utility_loss_drops_utility_supply_and_node() -> None:
    snapshot, result = _solve("utility_loss")
    assert "UTIL-001" not in {s.node_id for s in snapshot.sources}
    assert result["UTIL-001"].state is EnergizationState.DE_ENERGIZED


def test_utility_loss_critical_board_held_by_ups() -> None:
    _snapshot, result = _solve("utility_loss")
    assert result["DB-003"].state is EnergizationState.ENERGIZED_UPS


def test_ats_provides_backfed_alternate_path() -> None:
    # ATS-001 is the alternate source path into SWGR-LV-002; feeding the MV bus
    # back through TX-002 is a backfeed the solver must flag.
    _snapshot, result = _solve("utility_loss")
    tx2 = result["TX-002"]
    assert tx2.state is EnergizationState.ENERGIZED_BACKUP
    assert tx2.is_backfed is True
    assert "ATS-001" in tx2.path
    assert tx2.source_node_id == "GEN-001"


def test_ats_backfeed_edge_is_traversed_against_declared_direction() -> None:
    snapshot, result = _solve("utility_loss")
    winding = _edge_by_id(snapshot, "E-TX2-SWGRLV2")
    # Declared TX-002 -> SWGR-LV-002 ...
    assert winding.from_node_id == "TX-002"
    assert winding.to_node_id == "SWGR-LV-002"
    # ... but TX-002 is energized by coming *from* SWGR-LV-002 (reverse), via ATS.
    path = result["TX-002"].path
    assert path.index("ATS-001") < path.index("SWGR-LV-002") < path.index("TX-002")


def test_unknown_switch_variant_has_an_unknown_edge() -> None:
    snapshot = topology_snapshot("unknown_switch")
    unknown_edges = [e for e in snapshot.edges if e.switch_state is SwitchState.UNKNOWN]
    assert [e.id for e in unknown_edges] == ["E-LV2-MCC3"]


def test_unknown_switch_yields_indeterminate_without_guessing() -> None:
    _snapshot, result = _solve("unknown_switch")
    indeterminate = {
        node_id
        for node_id, r in result.items()
        if r.state is EnergizationState.INDETERMINATE
    }
    assert len(indeterminate) >= 1
    # It is exactly the branch reachable only through the UNKNOWN switch --
    # proving nothing behind it was guessed energized or de-energized.
    assert indeterminate == _MCC3_BRANCH
    for node_id in _MCC3_BRANCH:
        res = result[node_id]
        assert res.state is EnergizationState.INDETERMINATE
        assert res.state not in ENERGIZED_STATES
        assert res.state is not EnergizationState.DE_ENERGIZED
        assert res.indeterminate_reason is not None


def test_unknown_switch_leaves_healthy_network_definite() -> None:
    # The UNKNOWN MCC-003 incomer must not contaminate the rest of the plant.
    _snapshot, result = _solve("unknown_switch")
    for node_id in ("SWGR-LV-001", "SWGR-LV-002", "MCC-001", "MCC-002"):
        assert result[node_id].state is EnergizationState.ENERGIZED_PRIMARY


def test_topology_snapshot_is_deterministic() -> None:
    first = topology_snapshot("base")
    second = topology_snapshot("base")
    assert first.model_dump() == second.model_dump()
    assert first.captured_at == second.captured_at
    assert first.facility_id == "FAC-001"


def test_building_variants_does_not_mutate_shared_inventory() -> None:
    base_before = {e.id: e.switch_state for e in topology_snapshot("base").edges}
    topology_snapshot("tie_closed")
    topology_snapshot("utility_loss")
    topology_snapshot("unknown_switch")
    base_after = {e.id: e.switch_state for e in topology_snapshot("base").edges}
    assert base_before == base_after
