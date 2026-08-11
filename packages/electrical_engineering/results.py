"""Solver output types for the topology energization analysis.

These are the *result* value objects produced by :mod:`topology`. They carry no
I/O, no database access and no network access. The inputs to the solver are the
canonical pydantic models
(:class:`~packages.canonical_electrical_model.ElectricalNode`,
:class:`~packages.canonical_electrical_model.ElectricalEdge`,
:class:`~packages.canonical_electrical_model.SourceNode`); only the outputs live
here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from packages.canonical_electrical_model import (
    Criticality,
    EnergizationState,
)

#: States that represent a node that is definitely energized (reached from some
#: source over a path of exclusively CLOSED switches).
ENERGIZED_STATES: frozenset[EnergizationState] = frozenset(
    {
        EnergizationState.ENERGIZED_PRIMARY,
        EnergizationState.ENERGIZED_BACKUP,
        EnergizationState.ENERGIZED_UPS,
    }
)


@dataclass
class EnergizationResult:
    """Result of energization analysis for a single node."""

    node_id: str
    state: EnergizationState
    source_node_id: str | None = None
    path: list[str] = field(default_factory=list)
    is_backfed: bool = False
    indeterminate_reason: str | None = None


@dataclass(frozen=True)
class ImpactSet:
    """Set of nodes de-energized by the loss of some node, grouped by criticality.

    This is the reusable primitive for fault-consequence, N-1 resilience and
    load-shedding analyses in later work packages.

    A node whose criticality is unspecified (the canonical model allows
    :class:`~packages.canonical_electrical_model.ElectricalNode.criticality` to
    be ``None``) is grouped under the ``None`` key so that no impacted node is
    ever silently dropped.
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
