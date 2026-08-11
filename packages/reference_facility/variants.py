"""Topology switching variants for FAC-001.

:func:`topology_snapshot` returns the FAC-001 :class:`TopologySnapshot` with a
named switching state applied. The nodes and their impedances never change
between variants -- only the live switch states of edges, and (for
``utility_loss``) which supplies are present -- exactly as a real facility's
one-line stays fixed while breakers open and close.

Variants
--------
``base``
    Normal operation. Bus tie ``CB-TIE-001`` open, backup idle. Two
    independent, utility-fed 480 V islands.
``tie_closed``
    Bus tie closed. This ties both LV buses (and, through the two
    transformers and the shared MV bus, closes a genuine electrical loop). The
    solver must resolve it without looping forever.
``tx1_out``
    ``TX-001`` isolated (racked out) for maintenance; island A's load is
    transferred by closing the bus tie so it is fed from island B.
``utility_loss``
    Utility supply lost. The generator picks up island A directly and, through
    ``ATS-001``, backfeeds island B; the UPS holds the critical panel.
``unknown_switch``
    The ``TX-002`` low-voltage main (``E-TX2``) is in an UNKNOWN position
    (e.g. lost breaker-status telemetry). Everything reachable only through it
    must resolve to INDETERMINATE -- never a guess.
"""

from __future__ import annotations

from packages.canonical_electrical_model import (
    ElectricalEdge,
    SourceNode,
    SwitchState,
    TopologySnapshot,
)

from .facility import (
    CAPTURED_AT,
    FACILITY_ID,
    build_edges,
    build_nodes,
    build_sources,
)

#: The set of supported variant names, in a stable order.
VARIANTS: tuple[str, ...] = (
    "base",
    "tie_closed",
    "tx1_out",
    "utility_loss",
    "unknown_switch",
)


def _with_states(
    edges: list[ElectricalEdge],
    overrides: dict[str, SwitchState],
) -> list[ElectricalEdge]:
    """Return a copy of ``edges`` with the given edge switch states replaced.

    Inputs are not mutated; each overridden edge is rebuilt via
    ``model_copy`` so the returned list is independent of the base edges.
    """

    unknown_ids = set(overrides) - {edge.id for edge in edges}
    if unknown_ids:
        raise KeyError(f"unknown edge id(s): {sorted(unknown_ids)}")
    result: list[ElectricalEdge] = []
    for edge in edges:
        if edge.id in overrides:
            result.append(edge.model_copy(update={"switch_state": overrides[edge.id]}))
        else:
            result.append(edge.model_copy())
    return result


def _snapshot(
    variant: str,
    edges: list[ElectricalEdge],
    sources: list[SourceNode],
) -> TopologySnapshot:
    return TopologySnapshot(
        snapshot_id=f"{FACILITY_ID}-{variant}",
        facility_id=FACILITY_ID,
        captured_at=CAPTURED_AT,
        nodes=build_nodes(),
        edges=edges,
        sources=sources,
    )


def topology_snapshot(variant: str = "base") -> TopologySnapshot:
    """Return the FAC-001 topology snapshot for a named switching ``variant``.

    Parameters
    ----------
    variant:
        One of :data:`VARIANTS`. Defaults to ``"base"``.

    Raises
    ------
    ValueError
        If ``variant`` is not a recognised variant name.
    """

    base_edges = build_edges()
    sources = build_sources()

    if variant == "base":
        return _snapshot(variant, _with_states(base_edges, {}), sources)

    if variant == "tie_closed":
        return _snapshot(
            variant,
            _with_states(
                base_edges,
                {
                    "E-TIE-1": SwitchState.CLOSED,
                    "E-TIE-2": SwitchState.CLOSED,
                },
            ),
            sources,
        )

    if variant == "tx1_out":
        # TX-001 racked out on both sides; island A load transferred to island
        # B by closing the bus tie.
        return _snapshot(
            variant,
            _with_states(
                base_edges,
                {
                    "E-MV-TX1": SwitchState.RACKED_OUT,
                    "E-TX1": SwitchState.RACKED_OUT,
                    "E-TIE-1": SwitchState.CLOSED,
                    "E-TIE-2": SwitchState.CLOSED,
                },
            ),
            sources,
        )

    if variant == "utility_loss":
        # Utility lost: drop the utility supply and open its main breaker.
        # The generator picks up island A directly and, through the ATS, feeds
        # island B; the UPS continues to hold the critical panel.
        edges = _with_states(
            base_edges,
            {
                "E-UTIL": SwitchState.OPEN,
                "E-GEN": SwitchState.CLOSED,
                "E-ATS-GEN": SwitchState.CLOSED,
                "E-ATS-OUT": SwitchState.CLOSED,
            },
        )
        live_sources = [s for s in sources if s.node_id != "UTIL-001"]
        return _snapshot(variant, edges, live_sources)

    if variant == "unknown_switch":
        # The TX-002 LV main breaker position is UNKNOWN (lost telemetry).
        # Island B is reachable only through it, so it must be INDETERMINATE.
        return _snapshot(
            variant,
            _with_states(base_edges, {"E-TX2": SwitchState.UNKNOWN}),
            sources,
        )

    raise ValueError(
        f"unknown topology variant {variant!r}; expected one of {VARIANTS}"
    )
