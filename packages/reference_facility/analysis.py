"""Topology analysis helpers for the reference facility.

Small, pure graph utilities used by the tests (and available to callers) to
reason about a :class:`TopologySnapshot`:

* :func:`lv_islands` -- the electrically separate low-voltage islands, i.e. the
  groups of LV switchgear buses that are interconnected at the LV level over
  closed switches. Two LV buses on separate transformers with an open bus tie
  are two separate islands even though they share an upstream MV source; the
  interconnection through the transformers/MV bus is deliberately *not* treated
  as an LV tie.
* :func:`closed_graph_has_cycle` -- whether the closed-switch graph contains a
  cycle (a tie breaker closing a loop). Used to prove the ``tie_closed`` variant
  really does form a loop that the solver must terminate on.

Everything here is a pure function; nothing performs I/O.
"""

from __future__ import annotations

from packages.canonical_electrical_model import (
    AssetType,
    SwitchState,
    TopologySnapshot,
)

#: Nodes at or below this nominal voltage are considered low voltage.
LV_MAX_VOLTAGE_V = 1_000.0


def _lv_node_ids(snapshot: TopologySnapshot) -> set[str]:
    return {
        node.id
        for node in snapshot.nodes
        if node.nominal_voltage_v is not None
        and node.nominal_voltage_v <= LV_MAX_VOLTAGE_V
    }


def _lv_bus_ids(snapshot: TopologySnapshot, lv_nodes: set[str]) -> set[str]:
    return {
        node.id
        for node in snapshot.nodes
        if node.id in lv_nodes and node.asset_type is AssetType.SWITCHGEAR
    }


def _lv_closed_components(snapshot: TopologySnapshot) -> list[frozenset[str]]:
    """Connected components of the LV-only closed-switch subgraph.

    Only edges whose switch is CLOSED and whose *both* endpoints are LV nodes
    are traversed, so interconnection through a transformer (an MV node) never
    merges two LV islands.
    """

    lv_nodes = _lv_node_ids(snapshot)
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in lv_nodes}
    for edge in snapshot.edges:
        if edge.switch_state is not SwitchState.CLOSED:
            continue
        if edge.from_node_id in lv_nodes and edge.to_node_id in lv_nodes:
            adjacency[edge.from_node_id].add(edge.to_node_id)
            adjacency[edge.to_node_id].add(edge.from_node_id)

    seen: set[str] = set()
    components: list[frozenset[str]] = []
    for start in sorted(lv_nodes):
        if start in seen:
            continue
        stack = [start]
        component: set[str] = set()
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            component.add(current)
            stack.extend(adjacency[current] - seen)
        components.append(frozenset(component))
    return components


def lv_islands(snapshot: TopologySnapshot) -> list[frozenset[str]]:
    """Electrically separate LV islands, each as the set of LV bus ids in it.

    An "island" here is a connected component of the LV-only closed-switch
    subgraph that contains at least one LV switchgear bus; the returned
    frozenset lists the switchgear-bus ids in that component. The list is
    ordered deterministically by the sorted bus ids of each island.
    """

    bus_ids = _lv_bus_ids(snapshot, _lv_node_ids(snapshot))
    islands = [
        frozenset(component & bus_ids)
        for component in _lv_closed_components(snapshot)
        if component & bus_ids
    ]
    islands.sort(key=lambda buses: sorted(buses))
    return islands


def count_lv_islands(snapshot: TopologySnapshot) -> int:
    """Number of electrically separate LV islands (see :func:`lv_islands`)."""

    return len(lv_islands(snapshot))


def lv_island_of(snapshot: TopologySnapshot, node_id: str) -> frozenset[str]:
    """All LV node ids electrically bonded to ``node_id`` over closed switches.

    Returns the full LV connected component containing ``node_id`` (not just its
    buses), or an empty frozenset if ``node_id`` is not an LV node.
    """

    for component in _lv_closed_components(snapshot):
        if node_id in component:
            return component
    return frozenset()


def closed_graph_has_cycle(snapshot: TopologySnapshot) -> bool:
    """Whether the closed-switch graph contains a cycle (undirected).

    Uses union-find over all CLOSED edges: an edge whose two endpoints are
    already connected closes a loop. This is what makes ``tie_closed`` a real
    cycle rather than a tree.
    """

    parent: dict[str, str] = {}

    def find(node_id: str) -> str:
        parent.setdefault(node_id, node_id)
        root = node_id
        while parent[root] != root:
            root = parent[root]
        # Path compression.
        while parent[node_id] != root:
            parent[node_id], node_id = root, parent[node_id]
        return root

    for edge in snapshot.edges:
        if edge.switch_state is not SwitchState.CLOSED:
            continue
        a, b = find(edge.from_node_id), find(edge.to_node_id)
        if a == b:
            return True
        parent[a] = b
    return False
