"""Aggregate models for the synthetic reference facility FAC-001.

These models wrap the canonical electrical model (:mod:`packages.
canonical_electrical_model`) into a single, referentially-validated container.
They add no new *observed* or *rated* physics: they only assemble canonical
objects and assert their internal consistency.

Everything described here is synthetic (``DataProvenance.SYNTHETIC``). FAC-001 is
not based on, derived from, or a model of any real facility, site, customer,
partner, or vendor.
"""

from __future__ import annotations

from pydantic import model_validator

from packages.canonical_electrical_model import (
    CanonicalModel,
    ElectricalEdge,
    ElectricalNode,
    Facility,
    SourceNode,
)


class SubMeter(CanonicalModel):
    """A sub-meter and the node whose throughput it measures.

    This is a descriptive mapping only. It records *where metering coverage
    exists*; it is not a command and carries no setpoint.
    """

    meter_node_id: str
    measures_node_id: str


class MeteringPlan(CanonicalModel):
    """Sub-metering coverage for the facility, including an intentional gap.

    ``intentional_unmetered_branch_id`` names a branch that is *deliberately*
    left without a dedicated sub-meter so that the whole-plant energy balance
    has a genuine unmetered path to detect. This is a test fixture for the WP3
    unmetered-load detector; ``note`` documents that it must not be "fixed".
    """

    submeters: list[SubMeter]
    intentional_unmetered_branch_id: str
    intentional_gap_is_test_fixture: bool = True
    note: str

    @property
    def metered_node_ids(self) -> frozenset[str]:
        """Ids of nodes that a sub-meter directly measures."""
        return frozenset(sm.measures_node_id for sm in self.submeters)

    def is_metered(self, node_id: str) -> bool:
        """Whether *node_id* is directly measured by a sub-meter."""
        return node_id in self.metered_node_ids


class ReferenceFacility(CanonicalModel):
    """A validated, self-consistent synthetic facility (FAC-001).

    Wraps the canonical :class:`Facility`, its nodes, directed edges, supply
    sources, and its sub-metering plan. Construction fails unless every
    cross-reference resolves and every node id is unique, so a successfully
    constructed instance is guaranteed internally consistent.
    """

    facility: Facility
    nodes: list[ElectricalNode]
    edges: list[ElectricalEdge]
    sources: list[SourceNode]
    metering: MeteringPlan

    @property
    def node_ids(self) -> frozenset[str]:
        """The set of node ids in the facility."""
        return frozenset(node.id for node in self.nodes)

    def node(self, node_id: str) -> ElectricalNode:
        """Return the node with *node_id* (raises ``KeyError`` if absent)."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        raise KeyError(node_id)

    @property
    def unmetered_branch(self) -> ElectricalNode:
        """The node deliberately left without a dedicated sub-meter."""
        return self.node(self.metering.intentional_unmetered_branch_id)

    @model_validator(mode="after")
    def _check_referential_integrity(self) -> ReferenceFacility:
        ids = [node.id for node in self.nodes]
        id_set = set(ids)

        if len(ids) != len(id_set):
            duplicates = sorted({i for i in ids if ids.count(i) > 1})
            raise ValueError(f"duplicate node ids: {duplicates}")

        for node in self.nodes:
            if node.parent_facility_id != self.facility.id:
                raise ValueError(
                    f"node {node.id} references facility "
                    f"{node.parent_facility_id!r}, expected {self.facility.id!r}"
                )
            if node.rated is None:
                raise ValueError(f"node {node.id} is missing RatedData")
            if node.criticality is None:
                raise ValueError(f"node {node.id} is missing Criticality")

        for edge in self.edges:
            for ref in (edge.from_node_id, edge.to_node_id):
                if ref not in id_set:
                    raise ValueError(f"edge {edge.id} references unknown node {ref!r}")
            device = edge.switching_device_node_id
            if device is not None and device not in id_set:
                raise ValueError(
                    f"edge {edge.id} references unknown switching device {device!r}"
                )

        for source in self.sources:
            if source.node_id not in id_set:
                raise ValueError(
                    f"source references unknown node {source.node_id!r}"
                )

        for submeter in self.metering.submeters:
            for ref in (submeter.meter_node_id, submeter.measures_node_id):
                if ref not in id_set:
                    raise ValueError(f"metering plan references unknown node {ref!r}")

        gap = self.metering.intentional_unmetered_branch_id
        if gap not in id_set:
            raise ValueError(
                f"intentional_unmetered_branch_id references unknown node {gap!r}"
            )
        if self.metering.is_metered(gap):
            raise ValueError(
                f"branch {gap!r} is declared as the intentional metering gap but a "
                f"sub-meter measures it; the gap must remain unmetered"
            )

        return self
