"""Energization of the reference facility on the real engineering solver.

This adapts the canonical :class:`TopologySnapshot` into the pure engineering
primitives consumed by :func:`electrical_engineering.solve_energization`, runs
the solver, and exposes the result. No assumptions are made about ``UNKNOWN``
switches: the underlying solver reports nodes reachable only through an
``UNKNOWN`` switch as ``INDETERMINATE``.

The canonical and engineering layers keep independent, deliberately small
vocabularies. The mappings below are the single crossing point between them.
"""

from __future__ import annotations

from typing import Any

from packages.canonical_electrical_model import Criticality as CanonicalCriticality
from packages.canonical_electrical_model import SourceType as CanonicalSourceType
from packages.canonical_electrical_model import SwitchState as CanonicalSwitchState
from packages.canonical_electrical_model import TopologySnapshot
from packages.electrical_engineering import (
    Criticality,
    Edge,
    EnergizationResult,
    Node,
    SourceNode,
    SourceType,
    SwitchState,
    solve_energization,
)

from .topology import topology

# INTERMEDIATE is treated as UNKNOWN: a partially-open device might or might not
# conduct, so any node reachable only through it must be INDETERMINATE.
_SWITCH_STATE_MAP: dict[CanonicalSwitchState, SwitchState] = {
    CanonicalSwitchState.CLOSED: SwitchState.CLOSED,
    CanonicalSwitchState.OPEN: SwitchState.OPEN,
    CanonicalSwitchState.UNKNOWN: SwitchState.UNKNOWN,
    CanonicalSwitchState.INTERMEDIATE: SwitchState.UNKNOWN,
}

# The engineering solver only distinguishes source types it can assign an
# energized state to. Every source type used by the reference facility maps to
# one of these.
_SOURCE_TYPE_MAP: dict[CanonicalSourceType, SourceType] = {
    CanonicalSourceType.UTILITY: SourceType.UTILITY,
    CanonicalSourceType.GENERATOR: SourceType.GENERATOR,
    CanonicalSourceType.UPS: SourceType.UPS,
    CanonicalSourceType.BATTERY: SourceType.STORAGE,
}

_CRITICALITY_MAP: dict[CanonicalCriticality, Criticality] = {
    CanonicalCriticality.LIFE_SAFETY: Criticality.LIFE_SAFETY,
    CanonicalCriticality.CRITICAL: Criticality.CRITICAL,
    CanonicalCriticality.HIGH: Criticality.ESSENTIAL,
    CanonicalCriticality.MEDIUM: Criticality.ESSENTIAL,
    CanonicalCriticality.LOW: Criticality.NON_ESSENTIAL,
}


def _map_source_type(source_type: CanonicalSourceType) -> SourceType:
    try:
        return _SOURCE_TYPE_MAP[source_type]
    except KeyError as exc:  # pragma: no cover - guards future source types
        raise ValueError(
            f"Source type {source_type!r} has no engineering-solver mapping."
        ) from exc


def snapshot_to_engineering(
    snapshot: TopologySnapshot,
) -> tuple[list[Node], list[Edge], list[SourceNode]]:
    """Convert a canonical snapshot into engineering solver inputs."""

    nodes = [
        Node(
            node_id=node.id,
            criticality=_CRITICALITY_MAP.get(
                node.criticality, Criticality.NON_ESSENTIAL
            )
            if node.criticality is not None
            else Criticality.NON_ESSENTIAL,
            name=node.name,
        )
        for node in snapshot.nodes
    ]
    edges = [
        Edge(
            from_node_id=edge.from_node_id,
            to_node_id=edge.to_node_id,
            switch_state=_SWITCH_STATE_MAP[edge.switch_state],
            edge_id=edge.id,
        )
        for edge in snapshot.edges
    ]
    sources = [
        SourceNode(
            node_id=source.node_id,
            source_type=_map_source_type(source.source_type),
            priority=source.priority,
            name=source.node_id,
        )
        for source in snapshot.sources
    ]
    return nodes, edges, sources


def energize_snapshot(snapshot: TopologySnapshot) -> dict[str, EnergizationResult]:
    """Run the engineering solver over a canonical snapshot."""

    nodes, edges, sources = snapshot_to_engineering(snapshot)
    return solve_energization(nodes, edges, sources)


def energization(variant: str = "normal") -> dict[str, EnergizationResult]:
    """Solve energization for a named topology variant."""

    return energize_snapshot(topology(variant))


def energization_rows(variant: str = "normal") -> list[dict[str, Any]]:
    """Return a JSON-serialisable, deterministically-ordered result table."""

    results = energization(variant)
    rows = [
        {
            "node_id": result.node_id,
            "state": result.state.value,
            "source_node_id": result.source_node_id,
            "path": list(result.path),
            "is_backfed": result.is_backfed,
            "indeterminate_reason": result.indeterminate_reason,
        }
        for result in results.values()
    ]
    rows.sort(key=lambda row: str(row["node_id"]))
    return rows
