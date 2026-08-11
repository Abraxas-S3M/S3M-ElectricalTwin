"""Topology variants for the reference facility.

A *variant* is the base facility graph with a small set of switch-state
overrides applied. The node and edge inventory is identical across variants;
only the live ``switch_state`` of named edges changes. This mirrors real
operations, where the physical plant is fixed and only switching configuration
moves.

Each variant maps to a :class:`~canonical_electrical_model.TopologySnapshot`.
Snapshots are also produced by the replay engine at each switching change, so
this module additionally exposes :func:`build_snapshot`, which applies an
arbitrary set of edge overrides at a caller-supplied capture time.
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

from datetime import datetime

from packages.canonical_electrical_model import (
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
    FACILITY_ID,
    base_edges,
    base_nodes,
    base_sources,
)

#: A fixed, deterministic default capture time. The reference facility never
#: uses wall-clock time so that every artefact it produces is reproducible.
DEFAULT_CAPTURED_AT = datetime(2026, 1, 1, 0, 0, 0)

#: Per-variant switch-state overrides, keyed by edge id. ``normal`` applies no
#: override (the base edges already describe the normal configuration).
VARIANT_OVERRIDES: dict[str, dict[str, SwitchState]] = {
    "normal": {},
    # Utility lost; the standby generator has started and closed onto the board.
    "utility_outage": {
        "E-UTIL-XFMR": SwitchState.OPEN,
        "E-GEN-MSB": SwitchState.CLOSED,
    },
    # The bus tie is closed (both buses paralleled through the tie).
    "tie_closed": {
        "E-TIE-AB": SwitchState.CLOSED,
    },
    # Bus B feeder out for maintenance; bus B is carried by backfeed across the
    # closed tie from bus A.
    "partial_maintenance": {
        "E-MSB-BUSB": SwitchState.OPEN,
        "E-TIE-AB": SwitchState.CLOSED,
    },
    # The position of the bus A distribution feeder cannot be determined; nodes
    # reachable only through it are INDETERMINATE, never a guess.
    "sensor_dropout": {
        "E-BUSA-XFMRA": SwitchState.UNKNOWN,
    },
}

#: The set of valid variant names, in a stable order.
TOPOLOGY_VARIANTS: tuple[str, ...] = (
    "normal",
    "utility_outage",
    "tie_closed",
    "partial_maintenance",
    "sensor_dropout",
)


class UnknownVariantError(ValueError):
    """Raised when an unknown topology variant is requested."""


def _resolve_overrides(variant: str) -> dict[str, SwitchState]:
    if variant not in VARIANT_OVERRIDES:
        raise UnknownVariantError(
            f"Unknown topology variant {variant!r}; valid variants are: "
            f"{', '.join(TOPOLOGY_VARIANTS)}."
        )
    return VARIANT_OVERRIDES[variant]


def build_snapshot(
    overrides: dict[str, SwitchState],
    *,
    captured_at: datetime = DEFAULT_CAPTURED_AT,
    snapshot_id: str = "SNAP-REF",
) -> TopologySnapshot:
    """Build a topology snapshot from the base graph plus edge overrides.

    ``overrides`` maps edge id to the switch state that edge should take. Edge
    ids not present in ``overrides`` keep their base (normal) switch state. An
    override naming an unknown edge id is a programming error and raises.
    """

    edges = base_edges()
    known_ids = {edge.id for edge in edges}
    unknown = set(overrides) - known_ids
    if unknown:
        raise KeyError(
            f"Override(s) reference unknown edge id(s): {', '.join(sorted(unknown))}."
        )

    resolved = []
    for edge in edges:
        new_state = overrides.get(edge.id)
        if new_state is not None:
            edge = edge.model_copy(update={"switch_state": new_state})
        resolved.append(edge)

    return TopologySnapshot(
        snapshot_id=snapshot_id,
        facility_id=FACILITY_ID,
        captured_at=captured_at,
        nodes=base_nodes(),
        edges=resolved,
        sources=base_sources(),
    )


def topology(
    variant: str = "normal",
    *,
    captured_at: datetime = DEFAULT_CAPTURED_AT,
) -> TopologySnapshot:
    """Return the :class:`TopologySnapshot` for a named variant.

    Raises:
        UnknownVariantError: if ``variant`` is not a known variant name.
    """

    overrides = _resolve_overrides(variant)
    return build_snapshot(
        overrides,
        captured_at=captured_at,
        snapshot_id=f"SNAP-REF-{variant.upper()}",
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
