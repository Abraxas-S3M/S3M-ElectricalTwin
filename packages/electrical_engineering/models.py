"""Immutable data model for the electrical topology.

All model types are pure data carriers. They contain no I/O, no database
access and no network access. Instances are hashable value objects so they can
be used freely in sets and as dictionary keys.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional

from .enums import (
    Criticality,
    EnergizationState,
    SourceType,
    SwitchState,
)


@dataclass(frozen=True)
class Node:
    """A bus, panel, load or any other addressable point in the network."""

    node_id: str
    criticality: Criticality = Criticality.NON_ESSENTIAL
    name: str = ""


@dataclass(frozen=True)
class SourceNode:
    """An energization source.

    ``priority`` orders sources when more than one can energize the same node
    over closed paths; a lower value wins. The winning source's
    :class:`~electrical_engineering.enums.SourceType` determines the reported
    energized state.
    """

    node_id: str
    source_type: SourceType
    priority: int
    name: str = ""


@dataclass(frozen=True)
class Edge:
    """A conductor/switch connecting two nodes.

    The edge is electrically bidirectional when its switch is closed. The
    declared ``from_node_id -> to_node_id`` orientation records the *intended*
    direction of power flow; traversal against it is reported as backfeed.
    """

    from_node_id: str
    to_node_id: str
    switch_state: SwitchState
    edge_id: str = ""


@dataclass
class EnergizationResult:
    """Result of energization analysis for a single node."""

    node_id: str
    state: EnergizationState
    source_node_id: Optional[str] = None
    path: list[str] = field(default_factory=list)
    is_backfed: bool = False
    indeterminate_reason: Optional[str] = None


@dataclass(frozen=True)
class ImpactSet:
    """Set of nodes de-energized by the loss of some node, grouped by criticality.

    This is the reusable primitive for fault-consequence, N-1 resilience and
    load-shedding analyses in later work packages.
    """

    by_criticality: Mapping[Criticality, frozenset[str]] = field(
        default_factory=dict
    )

    @property
    def all_nodes(self) -> frozenset[str]:
        """Every impacted node id, across all criticality buckets."""
        result: set[str] = set()
        for members in self.by_criticality.values():
            result.update(members)
        return frozenset(result)

    def nodes_of(self, criticality: Criticality) -> frozenset[str]:
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
