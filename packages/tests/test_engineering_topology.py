"""Tests for the topology energization solver.

Scenarios covered include: a single utility source, generator failover through
an automatic transfer switch, an open tie breaker isolating a bus, UNKNOWN
switch states yielding INDETERMINATE (never a guess), backfeed flagging, a
cycle that terminates, source priority ordering, UPS/battery sourcing,
function purity, downstream_impact behaviour (criticality partitioning, leaf
nodes, and N-1 redundancy), and the determinate non-conducting switch states
(TRIPPED and RACKED_OUT).

The solver operates on the canonical pydantic model types; these tests build
:class:`ElectricalNode`, :class:`ElectricalEdge` and :class:`SourceNode`
directly.
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
    downstream_impact,
    solve_energization,
)


def node(node_id: str, criticality: Criticality | None = None) -> ElectricalNode:
    return ElectricalNode(
        id=node_id,
        name=node_id,
        asset_type=AssetType.BUS,
        phases=3,
        parent_facility_id="fac-1",
        criticality=criticality,
    )


def util(node_id: str, priority: int = 0) -> SourceNode:
    return SourceNode(node_id=node_id, source_type=SourceType.UTILITY, priority=priority)


def source(node_id: str, source_type: SourceType, priority: int = 0) -> SourceNode:
    return SourceNode(node_id=node_id, source_type=source_type, priority=priority)


def edge(a: str, b: str, state: SwitchState, edge_id: str = "") -> ElectricalEdge:
    return ElectricalEdge(
        id=edge_id or f"{a}->{b}",
        from_node_id=a,
        to_node_id=b,
        edge_kind=EdgeKind.FEEDER,
        switch_state=state,
    )


def closed(a: str, b: str, edge_id: str = "") -> ElectricalEdge:
    return edge(a, b, SwitchState.CLOSED, edge_id)


def open_(a: str, b: str, edge_id: str = "") -> ElectricalEdge:
    return edge(a, b, SwitchState.OPEN, edge_id)


def unknown(a: str, b: str, edge_id: str = "") -> ElectricalEdge:
    return edge(a, b, SwitchState.UNKNOWN, edge_id)


def test_single_utility_source_energizes_primary():
    nodes = [node("BUS"), node("LOAD")]
    edges = [closed("UTIL", "BUS"), closed("BUS", "LOAD")]
    sources = [util("UTIL")]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].state is EnergizationState.ENERGIZED_PRIMARY
    assert result["BUS"].state is EnergizationState.ENERGIZED_PRIMARY
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
    sources = [
        util("UTIL", priority=0),
        source("GEN", SourceType.GENERATOR, priority=1),
    ]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].state is EnergizationState.ENERGIZED_BACKUP
    assert result["LOAD"].source_node_id == "GEN"
    assert result["ATS"].state is EnergizationState.ENERGIZED_BACKUP


def test_open_tie_breaker_isolates_bus():
    # BUS_B is only reachable through an open tie breaker: de-energized.
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
    # The only path is OPEN (not UNKNOWN): the node is definitely de-energized.
    nodes = [node("LOAD")]
    edges = [open_("UTIL", "LOAD")]
    sources = [util("UTIL")]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].state is EnergizationState.DE_ENERGIZED


def test_tripped_switch_is_determinate_deenergized_not_indeterminate():
    # A TRIPPED breaker is a KNOWN non-conducting state. A node reachable only
    # across it must be DE_ENERGIZED, never INDETERMINATE. Getting this wrong
    # would blind the solver in exactly the situation it exists for.
    nodes = [node("LOAD")]
    edges = [edge("UTIL", "LOAD", SwitchState.TRIPPED)]
    sources = [util("UTIL")]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].state is EnergizationState.DE_ENERGIZED
    assert result["LOAD"].indeterminate_reason is None


def test_racked_out_switch_is_determinate_deenergized_not_indeterminate():
    # A RACKED_OUT breaker is likewise a KNOWN non-conducting state.
    nodes = [node("LOAD")]
    edges = [edge("UTIL", "LOAD", SwitchState.RACKED_OUT)]
    sources = [util("UTIL")]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].state is EnergizationState.DE_ENERGIZED
    assert result["LOAD"].indeterminate_reason is None


def test_intermediate_switch_is_determinate_deenergized_not_indeterminate():
    nodes = [node("LOAD")]
    edges = [edge("UTIL", "LOAD", SwitchState.INTERMEDIATE)]
    sources = [util("UTIL")]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].state is EnergizationState.DE_ENERGIZED
    assert result["LOAD"].indeterminate_reason is None


def test_backfeed_flagged_when_edge_traversed_against_direction():
    # Edge declared LOAD -> GEN, but energization flows GEN -> LOAD.
    nodes = [node("LOAD")]
    edges = [closed("LOAD", "GEN")]
    sources = [source("GEN", SourceType.GENERATOR, priority=0)]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].state is EnergizationState.ENERGIZED_BACKUP
    assert result["LOAD"].is_backfed is True


def test_no_backfeed_when_edge_traversed_with_direction():
    nodes = [node("LOAD")]
    edges = [closed("GEN", "LOAD")]
    sources = [source("GEN", SourceType.GENERATOR, priority=0)]

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
        assert len(result[node_id].path) == len(set(result[node_id].path))


def test_source_priority_determines_state_when_both_reachable():
    # LOAD reachable from utility (priority 0) and generator (priority 1) over
    # closed paths: utility wins.
    nodes = [node("LOAD")]
    edges = [closed("UTIL", "LOAD"), closed("GEN", "LOAD")]
    sources = [
        util("UTIL", priority=0),
        source("GEN", SourceType.GENERATOR, priority=1),
    ]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].state is EnergizationState.ENERGIZED_PRIMARY
    assert result["LOAD"].source_node_id == "UTIL"


def test_lower_priority_generator_wins_when_it_is_higher_priority_number_first():
    # Only the generator has a closed path; utility feed is open.
    nodes = [node("LOAD")]
    edges = [open_("UTIL", "LOAD"), closed("GEN", "LOAD")]
    sources = [
        util("UTIL", priority=0),
        source("GEN", SourceType.GENERATOR, priority=1),
    ]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].state is EnergizationState.ENERGIZED_BACKUP
    assert result["LOAD"].source_node_id == "GEN"


def test_ups_source_state():
    nodes = [node("LOAD")]
    edges = [closed("UPS1", "LOAD")]
    sources = [source("UPS1", SourceType.UPS, priority=0)]

    result = solve_energization(nodes, edges, sources)

    assert result["LOAD"].state is EnergizationState.ENERGIZED_UPS


def test_battery_source_reports_backup():
    nodes = [node("LOAD")]
    edges = [closed("BESS", "LOAD")]
    sources = [source("BESS", SourceType.BATTERY, priority=0)]

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


def test_solver_is_pure_inputs_not_mutated():
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

    assert impact.nodes_of(Criticality.CRITICAL) == frozenset({"L1"})
    assert impact.nodes_of(Criticality.HIGH) == frozenset({"L2"})
    assert impact.all_nodes == frozenset({"L1", "L2"})
    assert "MAIN_BUS" not in impact


def test_downstream_impact_on_leaf_node_is_empty():
    nodes = [
        node("MAIN_BUS"),
        node("L1", Criticality.CRITICAL),
    ]
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


def test_indeterminate_does_not_propagate_backfeed_guess():
    # Confirm indeterminate nodes carry a path and reason but stay uncertain.
    nodes = [node("A"), node("B")]
    edges = [closed("UTIL", "A"), unknown("A", "B", "maybe")]
    sources = [util("UTIL")]

    result = solve_energization(nodes, edges, sources)

    assert result["A"].state is EnergizationState.ENERGIZED_PRIMARY
    assert result["B"].state is EnergizationState.INDETERMINATE
    assert result["B"].path[0] == "UTIL"
    assert "maybe" in result["B"].indeterminate_reason
