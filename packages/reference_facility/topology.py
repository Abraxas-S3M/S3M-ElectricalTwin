"""Projection of the reference facility onto the canonical topology model.

:func:`topology_snapshot` returns a
:class:`~packages.canonical_electrical_model.TopologySnapshot` for a requested
topology variant. The snapshot is *observed/rated reality only*: nodes, directed
feeder edges with a live switch state, and prioritised sources. It carries no
setpoint or command.

The ``captured_at`` timestamp is a fixed synthetic constant so the snapshot is
deterministic and byte-identical across machines (no wall-clock read).
"""

from __future__ import annotations

from datetime import UTC, datetime

from packages.canonical_electrical_model import (
    EdgeImpedance,
    EdgeKind,
    ElectricalEdge,
    ElectricalNode,
    Provenance,
    Provenanced,
    ProvenanceSource,
    RatedData,
    SourceNode,
    SwitchState,
    TopologySnapshot,
)

from .facility import (
    NodeRole,
    ReferenceFacility,
    reference_facility,
)

_CAPTURED_AT = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

_SYNTHETIC = Provenance(source=ProvenanceSource.SYNTHETIC, method="reference_facility")


def _rated_for(role: NodeRole, kva: float) -> RatedData | None:
    if kva <= 0.0:
        return None
    return RatedData(
        kva=Provenanced(value=kva, provenance=_SYNTHETIC),
    )


def topology_snapshot(variant: str = "base") -> TopologySnapshot:
    """Return the canonical :class:`TopologySnapshot` for a topology ``variant``.

    Recognised variants are ``base``, ``gen_backup`` and ``tie_alt``; any other
    value falls back to the clean ``base`` topology. See
    :func:`packages.reference_facility.facility.reference_facility`.
    """

    facility: ReferenceFacility = reference_facility(variant)

    nodes: list[ElectricalNode] = []
    for node in facility.nodes:
        nodes.append(
            ElectricalNode(
                id=node.node_id,
                name=node.name,
                asset_type=node.asset_type,
                nominal_voltage_v=node.nominal_v_ll,
                phases=3,
                parent_facility_id=facility.facility_id,
                rated=_rated_for(node.role, node.rated_kva),
                provenance=_SYNTHETIC,
            )
        )

    edges: list[ElectricalEdge] = []
    for node in facility.nodes:
        if node.parent_id is None:
            continue
        edges.append(
            ElectricalEdge(
                id=f"E-{node.parent_id}-{node.node_id}",
                from_node_id=node.parent_id,
                to_node_id=node.node_id,
                edge_kind=(
                    EdgeKind.TRANSFORMER_WINDING
                    if node.role is NodeRole.TRANSFORMER
                    else EdgeKind.FEEDER
                ),
                switch_state=SwitchState.CLOSED,
                impedance=EdgeImpedance(
                    r_ohm=node.feeder_r_ohm,
                    x_ohm=node.feeder_x_ohm,
                ),
                provenance=_SYNTHETIC,
            )
        )

    for from_id, to_id in facility.tie_edges:
        edges.append(
            ElectricalEdge(
                id=f"TIE-{from_id}-{to_id}",
                from_node_id=from_id,
                to_node_id=to_id,
                edge_kind=EdgeKind.TIE,
                switch_state=SwitchState.OPEN,
                provenance=_SYNTHETIC,
            )
        )

    sources: list[SourceNode] = [
        SourceNode(
            node_id=source.node_id,
            source_type=source.source_type,
            rated_kva=source.rated_kva,
            priority=source.priority,
        )
        for source in facility.sources
    ]

    return TopologySnapshot(
        snapshot_id=f"SNAP-{facility.facility_id}-{facility.variant}",
        facility_id=facility.facility_id,
        captured_at=_CAPTURED_AT,
        nodes=nodes,
        edges=edges,
        sources=sources,
    )
