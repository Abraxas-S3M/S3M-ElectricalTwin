"""Topology energization solver -- the core deliverable of this chunk.

This module is *calculations only*. It defines no domain enumerations and no
asset models: every enumeration (:class:`EnergizationState`,
:class:`SwitchState`, :class:`SourceType`, :class:`Criticality`) and every asset
model (:class:`ElectricalNode`, :class:`ElectricalEdge`, :class:`SourceNode`) is
imported from :mod:`packages.canonical_electrical_model`. The only types defined
here are the *result contracts* of the two solver functions -- they are the
outputs of a calculation, not descriptions of an asset.

Two pure functions are provided:

* :func:`solve_energization` resolves the energization state of every node in a
  network from a set of prioritised sources, honouring switch states.
* :func:`downstream_impact` reports which nodes lose power if a given node is
  lost, partitioned by criticality.

Design invariants (all enforced by tests):

* Pure functions only. No I/O, no database, no network, no global mutable
  state. Inputs are never mutated.
* ``UNKNOWN`` (and the equally non-committal ``INTERMEDIATE``) switch state is
  never resolved by assumption. A node reachable only through such a switch is
  ``INDETERMINATE`` -- never a guess in either direction. This is the single
  most important behaviour here.
* Cycles (for example tie breakers) terminate; traversal uses a visited set.

Energization semantics
-----------------------
An edge conducts for certain only when its switch is ``CLOSED``. An ``OPEN``
switch never conducts. An ``UNKNOWN`` or ``INTERMEDIATE`` switch *might*
conduct. For each node we therefore reason over two graphs:

* the CLOSED-only graph -- edges that definitely conduct; and
* the CLOSED-or-ambiguous graph -- edges that might conduct.

A node reachable from a source in the CLOSED-only graph is definitely
energized. A node not reachable there but reachable in the CLOSED-or-ambiguous
graph can only be reached by traversing at least one non-committal switch, so it
is ``INDETERMINATE``. A node reachable in neither graph is ``DE_ENERGIZED``.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from packages.canonical_electrical_model import (
    Criticality,
    ElectricalEdge,
    ElectricalNode,
    EnergizationState,
    SourceNode,
    SourceType,
    SwitchState,
)

#: States that represent a node that is definitely energized (reached from some
#: source over a path of exclusively CLOSED switches). Derived from
#: :class:`EnergizationState`; this is a calculation helper, not a new enum.
ENERGIZED_STATES: frozenset[EnergizationState] = frozenset(
    {
        EnergizationState.ENERGIZED_PRIMARY,
        EnergizationState.ENERGIZED_BACKUP,
        EnergizationState.ENERGIZED_UPS,
    }
)

#: Switch states that definitely conduct.
_DEFINITELY_CONDUCTING: frozenset[SwitchState] = frozenset({SwitchState.CLOSED})

#: Switch states that are non-committal: they might conduct, but we do not know.
#: Reaching a node only through one of these yields ``INDETERMINATE`` -- never a
#: guess. ``OPEN`` is deliberately excluded: an open switch definitely does not
#: conduct, so it produces ``DE_ENERGIZED``, not ``INDETERMINATE``.
_AMBIGUOUS_CONDUCTING: frozenset[SwitchState] = frozenset(
    {SwitchState.UNKNOWN, SwitchState.INTERMEDIATE}
)

#: States that might conduct: definitely-conducting plus ambiguous.
_MAYBE_CONDUCTING: frozenset[SwitchState] = _DEFINITELY_CONDUCTING | _AMBIGUOUS_CONDUCTING


def _state_for_source(source_type: SourceType) -> EnergizationState:
    """Map a source type to the energized state it confers.

    Total and conservative: utility is primary, a UPS confers the UPS state, and
    every other source type (generator, battery/storage, solar, wind,
    cogeneration, other) is treated as backup.
    """

    if source_type is SourceType.UTILITY:
        return EnergizationState.ENERGIZED_PRIMARY
    if source_type is SourceType.UPS:
        return EnergizationState.ENERGIZED_UPS
    return EnergizationState.ENERGIZED_BACKUP


@dataclass(frozen=True)
class EnergizationResult:
    """Result of energization analysis for a single node.

    ``path`` is the source-to-node id sequence used to reach the node (empty for
    a de-energized node). ``is_backfed`` is true when any hop on the path was
    traversed against its declared ``from_node_id -> to_node_id`` direction.
    ``indeterminate_reason`` is populated only for ``INDETERMINATE`` nodes.
    """

    node_id: str
    state: EnergizationState
    source_node_id: str | None = None
    path: list[str] = field(default_factory=list)
    is_backfed: bool = False
    indeterminate_reason: str | None = None


@dataclass(frozen=True)
class ImpactSet:
    """Nodes de-energized by the loss of some node, grouped by criticality.

    This is the reusable primitive for fault-consequence, N-1 resilience and
    load-shedding analyses in later work packages. Nodes whose criticality is
    unspecified are grouped under the ``None`` key -- criticality is never
    invented.
    """

    by_criticality: Mapping[Criticality | None, frozenset[str]] = field(
        default_factory=dict
    )

    @property
    def all_nodes(self) -> frozenset[str]:
        """Every impacted node id, across all criticality buckets."""
        result: set[str] = set()
        for members in self.by_criticality.values():
            result.update(members)
        return frozenset(result)

    def nodes_of(self, criticality: Criticality | None) -> frozenset[str]:
        """Impacted node ids for a single criticality class."""
        return self.by_criticality.get(criticality, frozenset())

    def is_empty(self) -> bool:
        return not self.all_nodes

    def __len__(self) -> int:
        return len(self.all_nodes)

    def __contains__(self, node_id: object) -> bool:
        return node_id in self.all_nodes

    def __iter__(self):
        return iter(self.all_nodes)


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

    Each edge yields two traversals. The reverse traversal (from the declared
    ``to`` node to the declared ``from`` node) is marked as being against the
    declared direction so backfeed can be detected.
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

    Returns a parent map ``node_id -> (parent_id, edge_used, against_direction)``
    for every reachable node. The source maps to ``(None, None, False)``. A
    visited set (the parent map itself) guarantees termination even when the
    graph contains cycles (tie breakers, ring buses, backfeed loops).
    """

    parents: dict[str, tuple[str | None, ElectricalEdge | None, bool]] = {
        source_id: (None, None, False)
    }
    queue: deque[str] = deque([source_id])
    while queue:
        current = queue.popleft()
        for neighbour, edge, against in adjacency.get(current, ()):
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
        Conductors/switches between nodes, each carrying a live ``switch_state``.
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
    closed_adjacency = _build_adjacency(node_ids, edges, _DEFINITELY_CONDUCTING)
    maybe_adjacency = _build_adjacency(node_ids, edges, _MAYBE_CONDUCTING)

    ordered_sources = sorted(sources, key=lambda s: (s.priority, s.node_id))

    results: dict[str, EnergizationResult] = {}

    # Pass 1 -- definite energization over CLOSED-only edges, in priority order.
    for source in ordered_sources:
        parents = _bfs_from_source(source.node_id, closed_adjacency)
        state = _state_for_source(source.source_type)
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

    # Pass 2 -- INDETERMINATE nodes: reachable only through a non-committal
    # switch. We never resolve the ambiguity to energized or de-energized.
    for source in ordered_sources:
        parents = _bfs_from_source(source.node_id, maybe_adjacency)
        for reached_id in parents:
            if reached_id in results:
                continue  # already definite, or claimed by an earlier source
            path, is_backfed, edges_on_path = _reconstruct_path(
                reached_id, parents
            )
            ambiguous_edge_ids = [
                (edge.id or f"{edge.from_node_id}->{edge.to_node_id}")
                for edge in edges_on_path
                if edge.switch_state in _AMBIGUOUS_CONDUCTING
            ]
            reason = (
                "reachable only through non-committal switch state on edge(s): "
                + ", ".join(ambiguous_edge_ids)
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

    "Lost" means the node, any source attached to it, and its incident edges are
    removed from the network. A node is counted as impacted when it was
    energized before the loss and is de-energized after it. Nodes that merely
    become ``INDETERMINATE`` are *not* counted: we only report what we can
    confirm is lost. The result is partitioned by each impacted node's
    criticality.

    This is the shared primitive reused by fault-consequence, N-1 resilience and
    load-shedding analyses. It is intentionally implemented once, here.
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
