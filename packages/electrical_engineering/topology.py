"""Topology energization solver -- the core deliverable of this chunk.

Two pure functions are provided:

* :func:`solve_energization` resolves the energization state of every node in a
  network from a set of prioritised sources, honouring switch states.
* :func:`downstream_impact` reports which nodes lose power if a given node is
  lost, partitioned by criticality.

The solver operates directly on the canonical pydantic models
(:class:`~packages.canonical_electrical_model.ElectricalNode`,
:class:`~packages.canonical_electrical_model.ElectricalEdge`,
:class:`~packages.canonical_electrical_model.SourceNode`); the canonical model
is the single source of truth for the vocabulary it consumes.

Design invariants (all enforced by tests):

* Pure functions only. No I/O, no database, no network, no global mutable
  state. Inputs are never mutated.
* ``UNKNOWN`` switch state is never resolved by assumption. A node reachable
  only through an ``UNKNOWN`` switch is ``INDETERMINATE`` -- never a guess in
  either direction. This is the single most important behaviour here.
* Cycles (for example tie breakers) terminate; traversal uses a visited set.

Switch-state conduction semantics (safety-relevant)
---------------------------------------------------
An edge conducts if and only if its switch is ``CLOSED``. The other states are
handled as follows, and the distinction is deliberate:

* ``OPEN``, ``INTERMEDIATE``, ``TRIPPED`` and ``RACKED_OUT`` are all
  *determinate non-conducting* states. They are known positions that do not
  carry current. A node reachable only across such a switch is definitely
  ``DE_ENERGIZED``; these states never make a downstream node
  ``INDETERMINATE``.
* ``UNKNOWN`` is the only indeterminate state. It *might* conduct, so a node
  reachable only by traversing at least one ``UNKNOWN`` switch is
  ``INDETERMINATE``.

Getting this backwards -- treating ``TRIPPED`` or ``RACKED_OUT`` as indeterminate
-- would make every node downstream of a tripped breaker read as indeterminate,
which is precisely the situation where the solver matters most. A tripped or
racked-out breaker is a *known* de-energizing condition, not an unknown one.

To decide this, each node is reasoned over two graphs:

* the CLOSED-only graph -- edges that definitely conduct; and
* the CLOSED-or-UNKNOWN graph -- edges that might conduct.

A node reachable from a source in the CLOSED-only graph is definitely
energized. A node not reachable there but reachable in the CLOSED-or-UNKNOWN
graph can only be reached by traversing at least one ``UNKNOWN`` switch, so it
is ``INDETERMINATE``. A node reachable in neither graph is ``DE_ENERGIZED``.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from packages.canonical_electrical_model import (
    Criticality,
    ElectricalEdge,
    ElectricalNode,
    EnergizationState,
    SourceNode,
    SourceType,
    SwitchState,
)

from .results import (
    ENERGIZED_STATES,
    EnergizationResult,
    ImpactSet,
)

#: Every energization source yields a determinate energized state. Utility is
#: the primary supply and a UPS is reported distinctly; every other source type
#: is treated as a backup supply. This mapping preserves the original solver
#: semantics while covering the full canonical ``SourceType`` vocabulary.
_STATE_FOR_SOURCE_TYPE: dict[SourceType, EnergizationState] = {
    SourceType.UTILITY: EnergizationState.ENERGIZED_PRIMARY,
    SourceType.GENERATOR: EnergizationState.ENERGIZED_BACKUP,
    SourceType.UPS: EnergizationState.ENERGIZED_UPS,
    SourceType.BATTERY: EnergizationState.ENERGIZED_BACKUP,
    SourceType.SOLAR_PV: EnergizationState.ENERGIZED_BACKUP,
    SourceType.WIND: EnergizationState.ENERGIZED_BACKUP,
    SourceType.COGENERATION: EnergizationState.ENERGIZED_BACKUP,
    SourceType.OTHER: EnergizationState.ENERGIZED_BACKUP,
}


# An adjacency entry: (neighbour_node_id, edge, traversed_against_direction).
_Adjacency = dict[str, list[tuple[str, ElectricalEdge, bool]]]


def _collect_node_ids(
    nodes: Iterable[ElectricalNode],
    edges: Iterable[ElectricalEdge],
    sources: Iterable[SourceNode],
) -> set[str]:
    node_ids: set[str] = set()
    for node in nodes:
        node_ids.add(node.id)
    for source in sources:
        node_ids.add(source.node_id)
    for edge in edges:
        node_ids.add(edge.from_node_id)
        node_ids.add(edge.to_node_id)
    return node_ids


def _build_adjacency(
    node_ids: set[str],
    edges: Iterable[ElectricalEdge],
    conducting_states: frozenset[SwitchState],
) -> _Adjacency:
    """Build a bidirectional adjacency over conducting edges.

    Each undirected edge yields two traversals. The reverse traversal (from the
    declared ``to`` node to the declared ``from`` node) is marked as being
    against the declared direction so backfeed can be detected.
    """

    adjacency: _Adjacency = {node_id: [] for node_id in node_ids}
    for edge in edges:
        if edge.switch_state not in conducting_states:
            continue
        adjacency[edge.from_node_id].append((edge.to_node_id, edge, False))
        adjacency[edge.to_node_id].append((edge.from_node_id, edge, True))
    return adjacency


def _bfs_from_source(
    source_id: str,
    adjacency: _Adjacency,
) -> dict[str, tuple[str | None, ElectricalEdge | None, bool]]:
    """Breadth-first traversal from a single source.

    Returns a parent map: ``node_id -> (parent_id, edge_used, against_direction)``
    for every reachable node. The source maps to ``(None, None, False)``. A
    visited set guarantees termination even when the graph contains cycles.
    """

    parents: dict[str, tuple[str | None, ElectricalEdge | None, bool]] = {
        source_id: (None, None, False)
    }
    queue: deque[str] = deque([source_id])
    while queue:
        current = queue.popleft()
        for neighbour, edge, against in adjacency.get(current, ()):  # noqa: E501
            if neighbour in parents:
                continue
            parents[neighbour] = (current, edge, against)
            queue.append(neighbour)
    return parents


def _reconstruct_path(
    node_id: str,
    parents: dict[str, tuple[str | None, ElectricalEdge | None, bool]],
) -> tuple[list[str], bool, list[ElectricalEdge]]:
    """Rebuild the path from the source to ``node_id``.

    Returns ``(path, is_backfed, edges_on_path)`` where ``is_backfed`` is true
    when any hop was traversed against its declared direction.
    """

    path: list[str] = []
    edges_on_path: list[ElectricalEdge] = []
    is_backfed = False
    cursor: str | None = node_id
    while cursor is not None:
        path.append(cursor)
        parent, edge, against = parents[cursor]
        if edge is not None:
            edges_on_path.append(edge)
            if against:
                is_backfed = True
        cursor = parent
    path.reverse()
    edges_on_path.reverse()
    return path, is_backfed, edges_on_path


def solve_energization(
    nodes: Iterable[ElectricalNode],
    edges: Iterable[ElectricalEdge],
    sources: Iterable[SourceNode],
) -> dict[str, EnergizationResult]:
    """Resolve the energization state of every node.

    Parameters
    ----------
    nodes:
        The nodes of the network (loads, buses, panels, ...).
    edges:
        Conductors/switches between nodes.
    sources:
        Energization sources, each carrying a priority (lower wins) and a type.

    Returns
    -------
    dict[str, EnergizationResult]
        One result per node id referenced by ``nodes``, ``sources`` or
        ``edges``.
    """

    nodes = list(nodes)
    edges = list(edges)
    sources = list(sources)

    node_ids = _collect_node_ids(nodes, edges, sources)
    closed_adjacency = _build_adjacency(
        node_ids, edges, frozenset({SwitchState.CLOSED})
    )
    maybe_adjacency = _build_adjacency(
        node_ids, edges, frozenset({SwitchState.CLOSED, SwitchState.UNKNOWN})
    )

    ordered_sources = sorted(sources, key=lambda s: (s.priority, s.node_id))

    results: dict[str, EnergizationResult] = {}

    # Pass 1 -- definite energization over CLOSED-only edges, in priority order.
    for source in ordered_sources:
        parents = _bfs_from_source(source.node_id, closed_adjacency)
        state = _STATE_FOR_SOURCE_TYPE[source.source_type]
        for reached_id in parents:
            if reached_id in results:
                continue  # already claimed by a higher-priority source
            path, is_backfed, _edges = _reconstruct_path(reached_id, parents)
            results[reached_id] = EnergizationResult(
                node_id=reached_id,
                state=state,
                source_node_id=source.node_id,
                path=path,
                is_backfed=is_backfed,
            )

    # Pass 2 -- INDETERMINATE nodes: reachable only through an UNKNOWN switch.
    for source in ordered_sources:
        parents = _bfs_from_source(source.node_id, maybe_adjacency)
        for reached_id in parents:
            if reached_id in results:
                continue  # already definite, or claimed by earlier source
            path, is_backfed, edges_on_path = _reconstruct_path(
                reached_id, parents
            )
            unknown_edge_ids = [
                (edge.id or f"{edge.from_node_id}->{edge.to_node_id}")
                for edge in edges_on_path
                if edge.switch_state is SwitchState.UNKNOWN
            ]
            reason = (
                "reachable only through UNKNOWN switch state on edge(s): "
                + ", ".join(unknown_edge_ids)
            )
            results[reached_id] = EnergizationResult(
                node_id=reached_id,
                state=EnergizationState.INDETERMINATE,
                source_node_id=source.node_id,
                path=path,
                is_backfed=is_backfed,
                indeterminate_reason=reason,
            )

    # Pass 3 -- everything still unresolved is definitely de-energized.
    for node_id in node_ids:
        if node_id not in results:
            results[node_id] = EnergizationResult(
                node_id=node_id,
                state=EnergizationState.DE_ENERGIZED,
                source_node_id=None,
                path=[],
                is_backfed=False,
            )

    return results


def downstream_impact(
    node_id: str,
    nodes: Iterable[ElectricalNode],
    edges: Iterable[ElectricalEdge],
    sources: Iterable[SourceNode],
) -> ImpactSet:
    """Nodes that become ``DE_ENERGIZED`` when ``node_id`` is lost.

    "Lost" means the node and its incident edges are removed from the network.
    A node is counted as impacted when it was energized before the loss and is
    de-energized after it. The result is partitioned by each impacted node's
    criticality (nodes with no declared criticality are grouped under ``None``).

    This is the shared primitive reused by fault-consequence, N-1 resilience
    and load-shedding analyses. It is intentionally implemented once, here.
    """

    nodes = list(nodes)
    edges = list(edges)
    sources = list(sources)

    before = solve_energization(nodes, edges, sources)

    surviving_nodes = [n for n in nodes if n.id != node_id]
    surviving_sources = [s for s in sources if s.node_id != node_id]
    surviving_edges = [
        e
        for e in edges
        if e.from_node_id != node_id and e.to_node_id != node_id
    ]
    after = solve_energization(surviving_nodes, surviving_edges, surviving_sources)

    criticality_of: dict[str, Criticality | None] = {
        n.id: n.criticality for n in nodes
    }

    buckets: dict[Criticality | None, set[str]] = {}
    for other_id, before_result in before.items():
        if other_id == node_id:
            continue
        if before_result.state not in ENERGIZED_STATES:
            continue
        after_result = after.get(other_id)
        after_state = (
            after_result.state
            if after_result is not None
            else EnergizationState.DE_ENERGIZED
        )
        if after_state is EnergizationState.DE_ENERGIZED:
            criticality = criticality_of.get(other_id)
            buckets.setdefault(criticality, set()).add(other_id)

    by_criticality = {
        criticality: frozenset(members)
        for criticality, members in buckets.items()
    }
    return ImpactSet(by_criticality=by_criticality)
