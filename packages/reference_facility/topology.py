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
"""

from __future__ import annotations

from datetime import datetime

from packages.canonical_electrical_model import (
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
    )
