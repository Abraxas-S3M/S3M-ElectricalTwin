"""Tests for the electrical-engineering topology energization solver.

Scenarios: a single utility source; generator failover through an automatic
transfer switch; an open tie breaker isolating a bus; UNKNOWN switch state
yielding INDETERMINATE and never a guess; backfeed flagging; a cycle that
terminates; source-priority ordering; UPS/storage sourcing; function purity;
and downstream_impact behaviour (criticality partitioning, leaf nodes, and N-1
redundancy).

Every enumeration and asset model is imported from the canonical model; the
solver and its result contracts come from the calculations package.
"""

from __future__ import annotations

from packages.canonical_electrical_model import (
    AssetType,
    Criticality,
    EdgeKind,
    ElectricalEdge,
    ElectricalNode,
    EnergizationState,
    SourceNode,
    SourceType,
    SwitchState,
)
from packages.electrical_engineering import (
    EnergizationResult,
    ImpactSet,
    downstream_impact,
    solve_energization,
)


def node(
    node_id: str,
    criticality: Criticality | None = None,
    asset_type: AssetType = AssetType.BUSBAR,
) -> ElectricalNode:
    return ElectricalNode(
        id=node_id,
        name=node_id,
        asset_type=asset_type,
        phases=3,
        parent_facility_id="fac",
        criticality=criticality,
    )


def _edge(a: str, b: str, state: SwitchState, edge_id: str = "") -> ElectricalEdge:
    return ElectricalEdge(
        id=edge_id or f"{a}->{b}",
        from_node_id=a,
        to_node_id=b,
        edge_kind=EdgeKind.FEEDER,
        switch_state=state,
    )


def closed(a: str, b: str, edge_id: str = "") -> ElectricalEdge:
    return _edge(a, b, SwitchState.CLOSED, edge_id)


def open_(a: str, b: str, edge_id: str = "") -> ElectricalEdge:
    return _edge(a, b, SwitchState.OPEN, edge_id)


def unknown(a: str, b: str, edge_id: str = "") -> ElectricalEdge:
    return _edge(a, b, SwitchState.UNKNOWN, edge_id)


def intermediate(a: str, b: str, edge_id: str = "") -> ElectricalEdge:
    return _edge(a, b, SwitchState.INTERMEDIATE, edge_id)


def util(node_id: str, priority: int = 0) -> SourceNode:
    return SourceNode(node_id=node_id, source_type=SourceType.UTILITY, priority=priority)


def gen(node_id: str, priority: int = 1) -> SourceNode:
    return SourceNode(node_id=node_id, source_type=SourceType.GENERATOR, priority=priority)


def test_single_utility_source_energizes_primary():
    nodes = [node("BUS"), node("LOAD")]
    edges = [closed("UTIL", "BUS"), closed("BUS", "LOAD")]
    sources = [util("UTIL")]

    result = solve_energization(nodes, edges, sources)

    assert result["BUS"].state is EnergizationState.ENERGIZED_PRIMARY
    assert result["LOAD"].state is EnergizationState.ENERGIZED_PRIMARY
    assert result["LOAD"].source_node_id == "UTIL"
    assert result["LOAD"].path == ["UTIL", "BUS", "LOAD"]
    assert result["LOAD"].is_backfed is False


def test_generator_failover_through_ats():
    # Utility feed to the ATS is open (utility lost); generator feed is closed.
    nodes = [node("ATS"), node("LOAD")]
    edges = [
        open_("UTIL", "ATS", "utility-breaker"),
        closed("GEN", "ATS", "gen-breaker"),
        closed("ATS", "LOAD"),
    ]
    sources = [util("UTIL", priority=0), gen("GEN", priority=1)]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].state is EnergizationState.ENERGIZED_BACKUP
    assert result["LOAD"].source_node_id == "GEN"
    assert result["ATS"].state is EnergizationState.ENERGIZED_BACKUP


def test_open_tie_breaker_isolates_bus():
    nodes = [node("BUS_A"), node("BUS_B")]
    edges = [closed("UTIL", "BUS_A"), open_("BUS_A", "BUS_B", "tie")]
    sources = [util("UTIL")]

    result = solve_energization(nodes, edges, sources)

    assert result["BUS_A"].state is EnergizationState.ENERGIZED_PRIMARY
    assert result["BUS_B"].state is EnergizationState.DE_ENERGIZED
    assert result["BUS_B"].path == []


def test_closed_tie_breaker_energizes_second_bus():
    nodes = [node("BUS_A"), node("BUS_B")]
    edges = [closed("UTIL", "BUS_A"), closed("BUS_A", "BUS_B", "tie")]
    sources = [util("UTIL")]

    result = solve_energization(nodes, edges, sources)

    assert result["BUS_B"].state is EnergizationState.ENERGIZED_PRIMARY


def test_unknown_switch_yields_indeterminate():
    nodes = [node("BUS"), node("LOAD")]
    edges = [unknown("UTIL", "BUS", "sw-unknown"), closed("BUS", "LOAD")]
    sources = [util("UTIL")]

    result = solve_energization(nodes, edges, sources)

    assert result["BUS"].state is EnergizationState.INDETERMINATE
    assert result["LOAD"].state is EnergizationState.INDETERMINATE
    assert result["LOAD"].indeterminate_reason is not None
    assert "sw-unknown" in result["LOAD"].indeterminate_reason


def test_unknown_never_resolved_as_energized_or_deenergized():
    # An INDETERMINATE node must be neither energized nor de-energized: no guess.
    nodes = [node("LOAD")]
    edges = [unknown("UTIL", "LOAD")]
    sources = [util("UTIL")]

    result = solve_energization(nodes, edges, sources)

    state = result["LOAD"].state
    assert state is EnergizationState.INDETERMINATE
    assert state is not EnergizationState.ENERGIZED_PRIMARY
    assert state is not EnergizationState.DE_ENERGIZED


def test_intermediate_switch_also_yields_indeterminate():
    # INTERMEDIATE is equally non-committal: never assumed open or closed.
    nodes = [node("LOAD")]
    edges = [intermediate("UTIL", "LOAD", "sw-mid")]
    sources = [util("UTIL")]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].state is EnergizationState.INDETERMINATE
    assert "sw-mid" in result["LOAD"].indeterminate_reason


def test_definite_closed_path_wins_over_unknown_alternative():
    # LOAD reachable via a CLOSED path and, separately, an UNKNOWN path.
    # The definite path must win: ENERGIZED, not INDETERMINATE.
    nodes = [node("BUS_C"), node("BUS_U"), node("LOAD")]
    edges = [
        closed("UTIL", "BUS_C"),
        closed("BUS_C", "LOAD"),
        unknown("UTIL", "BUS_U"),
        unknown("BUS_U", "LOAD"),
    ]
    sources = [util("UTIL")]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].state is EnergizationState.ENERGIZED_PRIMARY


def test_open_only_path_is_deenergized_not_indeterminate():
    nodes = [node("LOAD")]
    edges = [open_("UTIL", "LOAD")]
    sources = [util("UTIL")]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].state is EnergizationState.DE_ENERGIZED


def test_backfeed_flagged_when_edge_traversed_against_direction():
    # Edge declared LOAD -> GEN, but energization flows GEN -> LOAD.
    nodes = [node("LOAD")]
    edges = [
        ElectricalEdge(
            id="e",
            from_node_id="LOAD",
            to_node_id="GEN",
            edge_kind=EdgeKind.FEEDER,
            switch_state=SwitchState.CLOSED,
        )
    ]
    sources = [gen("GEN", priority=0)]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].state is EnergizationState.ENERGIZED_BACKUP
    assert result["LOAD"].is_backfed is True


def test_no_backfeed_when_edge_traversed_with_direction():
    nodes = [node("LOAD")]
    edges = [closed("GEN", "LOAD")]
    sources = [gen("GEN", priority=0)]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].is_backfed is False


def test_cycle_terminates_and_resolves():
    # Ring topology with a tie breaker closing the loop must not loop forever.
    nodes = [node("A"), node("B"), node("C")]
    edges = [
        closed("UTIL", "A"),
        closed("A", "B"),
        closed("B", "C"),
        closed("C", "A", "tie-loop"),
    ]
    sources = [util("UTIL")]

    result = solve_energization(nodes, edges, sources)

    for node_id in ("A", "B", "C"):
        assert result[node_id].state is EnergizationState.ENERGIZED_PRIMARY
        # A path visits no node twice.
        assert len(result[node_id].path) == len(set(result[node_id].path))


def test_source_priority_determines_state_when_both_reachable():
    # LOAD reachable from utility (priority 0) and generator (priority 1) over
    # closed paths: utility wins.
    nodes = [node("LOAD")]
    edges = [closed("UTIL", "LOAD"), closed("GEN", "LOAD")]
    sources = [util("UTIL", priority=0), gen("GEN", priority=1)]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].state is EnergizationState.ENERGIZED_PRIMARY
    assert result["LOAD"].source_node_id == "UTIL"


def test_generator_wins_when_only_it_has_a_closed_path():
    nodes = [node("LOAD")]
    edges = [open_("UTIL", "LOAD"), closed("GEN", "LOAD")]
    sources = [util("UTIL", priority=0), gen("GEN", priority=1)]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].state is EnergizationState.ENERGIZED_BACKUP
    assert result["LOAD"].source_node_id == "GEN"


def test_ups_source_state():
    nodes = [node("LOAD")]
    edges = [closed("UPS1", "LOAD")]
    sources = [SourceNode(node_id="UPS1", source_type=SourceType.UPS, priority=0)]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].state is EnergizationState.ENERGIZED_UPS


def test_battery_storage_source_reports_backup():
    nodes = [node("LOAD")]
    edges = [closed("BESS", "LOAD")]
    sources = [SourceNode(node_id="BESS", source_type=SourceType.BATTERY, priority=0)]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].state is EnergizationState.ENERGIZED_BACKUP


def test_all_referenced_nodes_present_in_result():
    nodes = [node("BUS"), node("LOAD")]
    edges = [closed("UTIL", "BUS"), open_("BUS", "ORPHAN")]
    sources = [util("UTIL")]

    result = solve_energization(nodes, edges, sources)

    assert set(result) == {"UTIL", "BUS", "LOAD", "ORPHAN"}


def test_deenergized_node_has_empty_path_and_no_source():
    nodes = [node("ISLAND")]
    edges: list[ElectricalEdge] = []
    sources = [util("UTIL")]

    result = solve_energization(nodes, edges, sources)

    assert result["ISLAND"].state is EnergizationState.DE_ENERGIZED
    assert result["ISLAND"].path == []
    assert result["ISLAND"].source_node_id is None


def test_solver_is_pure_and_deterministic():
    nodes = [node("BUS"), node("LOAD")]
    edges = [closed("UTIL", "BUS"), closed("BUS", "LOAD")]
    sources = [util("UTIL")]
    nodes_snapshot = list(nodes)
    edges_snapshot = list(edges)
    sources_snapshot = list(sources)

    first = solve_energization(nodes, edges, sources)
    second = solve_energization(nodes, edges, sources)

    assert nodes == nodes_snapshot
    assert edges == edges_snapshot
    assert sources == sources_snapshot
    assert {k: v.state for k, v in first.items()} == {
        k: v.state for k, v in second.items()
    }


def test_result_contract_shape():
    nodes = [node("LOAD")]
    edges = [closed("UTIL", "LOAD")]
    sources = [util("UTIL")]

    result = solve_energization(nodes, edges, sources)["LOAD"]

    assert isinstance(result, EnergizationResult)
    assert result.node_id == "LOAD"
    assert result.indeterminate_reason is None


def test_downstream_impact_partitions_by_criticality():
    nodes = [
        node("MAIN_BUS"),
        node("L1", Criticality.CRITICAL),
        node("L2", Criticality.HIGH),
    ]
    edges = [
        closed("UTIL", "MAIN_BUS"),
        closed("MAIN_BUS", "L1"),
        closed("MAIN_BUS", "L2"),
    ]
    sources = [util("UTIL")]

    impact = downstream_impact("MAIN_BUS", nodes, edges, sources)

    assert isinstance(impact, ImpactSet)
    assert impact.nodes_of(Criticality.CRITICAL) == frozenset({"L1"})
    assert impact.nodes_of(Criticality.HIGH) == frozenset({"L2"})
    assert impact.all_nodes == frozenset({"L1", "L2"})
    assert "MAIN_BUS" not in impact


def test_downstream_impact_on_leaf_node_is_empty():
    nodes = [node("MAIN_BUS"), node("L1", Criticality.CRITICAL)]
    edges = [closed("UTIL", "MAIN_BUS"), closed("MAIN_BUS", "L1")]
    sources = [util("UTIL")]

    impact = downstream_impact("L1", nodes, edges, sources)

    assert impact.is_empty()
    assert len(impact) == 0
    assert impact.all_nodes == frozenset()


def test_downstream_impact_excludes_redundantly_fed_nodes():
    # LOAD is fed from two buses; losing one bus does not de-energize it.
    nodes = [node("BUS_A"), node("BUS_B"), node("LOAD", Criticality.CRITICAL)]
    edges = [
        closed("UTIL", "BUS_A"),
        closed("UTIL", "BUS_B"),
        closed("BUS_A", "LOAD"),
        closed("BUS_B", "LOAD"),
    ]
    sources = [util("UTIL")]

    impact = downstream_impact("BUS_A", nodes, edges, sources)

    assert "LOAD" not in impact


def test_downstream_impact_of_source_deenergizes_dependents():
    nodes = [node("BUS"), node("LOAD", Criticality.LIFE_SAFETY)]
    edges = [closed("UTIL", "BUS"), closed("BUS", "LOAD")]
    sources = [util("UTIL")]

    impact = downstream_impact("UTIL", nodes, edges, sources)

    assert impact.nodes_of(Criticality.LIFE_SAFETY) == frozenset({"LOAD"})
    assert "BUS" in impact


def test_downstream_impact_groups_unspecified_criticality_under_none():
    nodes = [node("BUS"), node("LOAD")]  # LOAD criticality unspecified
    edges = [closed("UTIL", "BUS"), closed("BUS", "LOAD")]
    sources = [util("UTIL")]

    impact = downstream_impact("BUS", nodes, edges, sources)

    assert impact.nodes_of(None) == frozenset({"LOAD"})


def test_indeterminate_carries_path_and_reason_without_backfeed_guess():
    nodes = [node("A"), node("B")]
    edges = [closed("UTIL", "A"), unknown("A", "B", "maybe")]
    sources = [util("UTIL")]

    result = solve_energization(nodes, edges, sources)

    assert result["A"].state is EnergizationState.ENERGIZED_PRIMARY
    assert result["B"].state is EnergizationState.INDETERMINATE
    assert result["B"].path[0] == "UTIL"
    assert "maybe" in result["B"].indeterminate_reason
