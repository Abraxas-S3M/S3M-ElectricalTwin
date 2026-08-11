"""FAC-001 topology snapshots and switching variants (WP1.2).

WP1.1 (:mod:`packages.reference_facility.loader`) owns the FAC-001 *asset
inventory* -- the nodes, directed edges, supplies and metering plan. This module
adds the two things WP1.2 is responsible for, as a thin layer on top of that
inventory:

1. **Series impedances on every edge.** WP1.1's edges carry ratings and live
   switch state but no series impedance; the WP2 power-flow engine needs an
   ``r``/``x`` on every conductor and a derived impedance on every transformer
   winding. :func:`topology_snapshot` returns a canonical
   :class:`~packages.canonical_electrical_model.TopologySnapshot` whose edges are
   fully populated with synthetic-but-plausible impedances. Transformer-winding
   impedances are derived from the transformer's rated ``%Z`` (already carried by
   the WP1.1 inventory) so the two stay consistent.

2. **Named switching variants.** The physical network never changes between
   variants -- only the *observed* switch positions (and, for ``utility_loss``,
   which supplies are present). This mirrors how a real one-line stays fixed
   while breakers open and close.

Variants
--------
``base``
    Normal operation. Bus tie ``CB-TIE-001`` open, generator/ATS idle: two
    independent, utility-fed LV islands.
``tie_closed``
    Bus tie closed. This ties both LV buses and, through the two transformers
    and the shared MV bus, closes a genuine electrical loop; the solver must
    terminate on it rather than loop forever.
``tx1_out``
    ``TX-001`` racked out for maintenance; island A's load is transferred by
    closing the bus tie so it is fed from island B.
``utility_loss``
    Utility supply lost. The generator picks up through ``ATS-001`` (an
    alternate source path into ``SWGR-LV-002``, which backfeeds the MV bus
    through ``TX-002``); the UPS, on battery, holds the critical board.
``unknown_switch``
    The ``TX-002`` LV main (``E-TX2-SWGRLV2``) is in an UNKNOWN position
    (e.g. lost breaker-status telemetry). Everything reachable only through it
    must resolve to INDETERMINATE -- never a guess.

Everything here is a pure function over synthetic data. Nothing performs I/O
beyond WP1.1's one-time inventory load, and switch states are *observed*
positions only -- never a command or setpoint.
"""

from __future__ import annotations

from datetime import UTC, datetime

from packages.canonical_electrical_model import (
    AssetType,
    EdgeImpedance,
    ElectricalEdge,
    ElectricalNode,
    SourceNode,
    SwitchState,
    TopologySnapshot,
)

from .loader import load_reference_facility

FACILITY_ID = "FAC-001"

#: Nodes at or below this nominal voltage are treated as low voltage.
LV_MAX_VOLTAGE_V = 1_000.0

#: A fixed, deterministic capture time. A topology snapshot of a static fixture
#: must never depend on wall-clock time.
CAPTURED_AT = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

#: Supported variant names, in a stable order.
VARIANTS: tuple[str, ...] = (
    "base",
    "tie_closed",
    "tx1_out",
    "utility_loss",
    "unknown_switch",
)

# Per-edge-kind synthetic cable geometry. Lengths are plausible metres for the
# respective run; the per-metre series values are scaled by conductor ampacity
# (a larger conductor has a lower ohms-per-metre). All values are synthetic.
_LENGTH_M_BY_KIND: dict[str, float] = {
    "SOURCE_CONNECTION": 30.0,
    "TIE": 8.0,
    "FEEDER": 40.0,
    "TRANSFORMER_WINDING": 0.0,
}
_REF_AMPACITY_A = 630.0
_R_PER_M_AT_REF = 6.0e-5
_X_PER_M_AT_REF = 8.0e-5

# Transformer winding impedance split. A distribution transformer is strongly
# reactive; this X/R (~10) is a synthetic but representative split of the total
# %Z-derived series impedance into resistance and reactance.
_TX_R_FRACTION = 0.100
_TX_X_FRACTION = 0.995


def _transformer_winding_impedance(
    winding_edge: ElectricalEdge,
    node_by_id: dict[str, ElectricalNode],
) -> EdgeImpedance:
    """Series impedance of a transformer winding, derived from its rated %Z.

    ``Z_ohm = (%Z / 100) * V_secondary^2 / (kVA * 1000)`` referred to the LV
    (secondary) side, then split into resistance and reactance. Falls back to a
    small default only if the transformer lacks rated data (it should not).
    """

    transformer = node_by_id.get(winding_edge.from_node_id)
    secondary = node_by_id.get(winding_edge.to_node_id)
    rated = transformer.rated if transformer is not None else None
    secondary_v = secondary.nominal_voltage_v if secondary is not None else None
    if (
        rated is not None
        and rated.impedance_percent is not None
        and rated.kva is not None
        and secondary_v
    ):
        percent_z = rated.impedance_percent.value
        kva = rated.kva.value
        z_ohm = (percent_z / 100.0) * (secondary_v**2) / (kva * 1000.0)
        return EdgeImpedance(
            r_ohm=round(z_ohm * _TX_R_FRACTION, 6),
            x_ohm=round(z_ohm * _TX_X_FRACTION, 6),
            length_m=None,
        )
    return EdgeImpedance(r_ohm=0.0021, x_ohm=0.0086, length_m=None)


def _cable_impedance(edge: ElectricalEdge) -> EdgeImpedance:
    """Synthetic series impedance for a cable/bus run, scaled by ampacity."""

    length_m = _LENGTH_M_BY_KIND.get(edge.edge_kind.value, 40.0)
    ampacity = edge.ampacity_a or 100.0
    scale = _REF_AMPACITY_A / ampacity
    return EdgeImpedance(
        r_ohm=round(_R_PER_M_AT_REF * scale * length_m, 6),
        x_ohm=round(_X_PER_M_AT_REF * scale * length_m, 6),
        length_m=length_m,
    )


def _edge_impedance(
    edge: ElectricalEdge,
    node_by_id: dict[str, ElectricalNode],
) -> EdgeImpedance:
    if edge.edge_kind is edge.edge_kind.TRANSFORMER_WINDING:
        return _transformer_winding_impedance(edge, node_by_id)
    return _cable_impedance(edge)


def _base_edges_with_impedance() -> tuple[
    list[ElectricalNode], list[ElectricalEdge], list[SourceNode]
]:
    """FAC-001 nodes/edges/sources with a series impedance on every edge.

    The WP1.1 inventory is the source of truth; this copies its edges and adds
    the impedance WP2 power flow needs, without mutating the loaded facility.
    """

    facility = load_reference_facility()
    node_by_id = {node.id: node for node in facility.nodes}
    edges = [
        edge.model_copy(update={"impedance": _edge_impedance(edge, node_by_id)})
        for edge in facility.edges
    ]
    return list(facility.nodes), edges, list(facility.sources)


def _apply_switch_states(
    edges: list[ElectricalEdge],
    overrides: dict[str, SwitchState],
) -> list[ElectricalEdge]:
    unknown_ids = set(overrides) - {edge.id for edge in edges}
    if unknown_ids:
        raise KeyError(f"unknown edge id(s): {sorted(unknown_ids)}")
    return [
        edge.model_copy(update={"switch_state": overrides[edge.id]})
        if edge.id in overrides
        else edge
        for edge in edges
    ]


# Per-variant edge switch-state overrides (empty means base state).
_VARIANT_EDGE_OVERRIDES: dict[str, dict[str, SwitchState]] = {
    "base": {},
    "tie_closed": {"E-TIE": SwitchState.CLOSED},
    "tx1_out": {
        "E-SWGRMV-TX1": SwitchState.RACKED_OUT,
        "E-TX1-SWGRLV1": SwitchState.RACKED_OUT,
        "E-TIE": SwitchState.CLOSED,
    },
    "utility_loss": {
        "E-UTIL-SWGRMV": SwitchState.OPEN,
        "E-GEN-ATS": SwitchState.CLOSED,
        "E-ATS-LV2": SwitchState.CLOSED,
        # UPS transfers to battery: its rectifier input from SWGR-LV-002 opens,
        # so its output island is held by the UPS itself rather than back-claimed
        # by the generator through the switchboard.
        "E-LV2-UPS": SwitchState.OPEN,
    },
    # The MCC-003 incomer breaker position is UNKNOWN (lost breaker-status
    # telemetry). MCC-003 and everything below it is fed only through this one
    # switch and has no internal source, so the whole branch must resolve to
    # INDETERMINATE rather than being guessed either way.
    "unknown_switch": {"E-LV2-MCC3": SwitchState.UNKNOWN},
}


def _variant_sources(variant: str, sources: list[SourceNode]) -> list[SourceNode]:
    if variant == "utility_loss":
        # The utility supply is lost; every backup supply remains.
        return [s for s in sources if s.node_id != "UTIL-001"]
    return sources


def topology_snapshot(variant: str = "base") -> TopologySnapshot:
    """Return the FAC-001 topology snapshot for a named switching ``variant``.

    The returned :class:`TopologySnapshot` has a series impedance populated on
    every edge (ready for WP2 power flow) and the switch states of the requested
    variant applied.

    Parameters
    ----------
    variant:
        One of :data:`VARIANTS`. Defaults to ``"base"``.

    Raises
    ------
    ValueError
        If ``variant`` is not a recognised variant name.
    """

    if variant not in _VARIANT_EDGE_OVERRIDES:
        raise ValueError(
            f"unknown topology variant {variant!r}; expected one of {VARIANTS}"
        )

    nodes, edges, sources = _base_edges_with_impedance()
    edges = _apply_switch_states(edges, _VARIANT_EDGE_OVERRIDES[variant])
    return TopologySnapshot(
        snapshot_id=f"{FACILITY_ID}-{variant}",
        facility_id=FACILITY_ID,
        captured_at=CAPTURED_AT,
        nodes=nodes,
        edges=edges,
        sources=_variant_sources(variant, sources),
    )


# --------------------------------------------------------------------------- #
# Graph analysis helpers
# --------------------------------------------------------------------------- #


def _lv_node_ids(snapshot: TopologySnapshot) -> set[str]:
    return {
        node.id
        for node in snapshot.nodes
        if node.nominal_voltage_v is not None
        and node.nominal_voltage_v <= LV_MAX_VOLTAGE_V
    }


def _lv_switchgear_bus_ids(snapshot: TopologySnapshot, lv_nodes: set[str]) -> set[str]:
    return {
        node.id
        for node in snapshot.nodes
        if node.id in lv_nodes and node.asset_type is AssetType.SWITCHGEAR
    }


def _lv_closed_components(snapshot: TopologySnapshot) -> list[frozenset[str]]:
    """Connected components of the LV-only closed-switch subgraph.

    Only CLOSED edges whose *both* endpoints are LV nodes are traversed, so an
    interconnection through a transformer (an MV node) never merges two LV
    islands.
    """

    lv_nodes = _lv_node_ids(snapshot)
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in lv_nodes}
    for edge in snapshot.edges:
        if edge.switch_state is not SwitchState.CLOSED:
            continue
        if edge.from_node_id in lv_nodes and edge.to_node_id in lv_nodes:
            adjacency[edge.from_node_id].add(edge.to_node_id)
            adjacency[edge.to_node_id].add(edge.from_node_id)

    seen: set[str] = set()
    components: list[frozenset[str]] = []
    for start in sorted(lv_nodes):
        if start in seen:
            continue
        stack = [start]
        component: set[str] = set()
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            component.add(current)
            stack.extend(adjacency[current] - seen)
        components.append(frozenset(component))
    return components


def lv_islands(snapshot: TopologySnapshot) -> list[frozenset[str]]:
    """Electrically separate LV islands, each as the set of LV bus ids in it.

    An island is a connected component of the LV-only closed-switch subgraph
    that contains at least one LV switchgear bus; the frozenset lists the
    switchgear-bus ids in that component. Ordered deterministically.
    """

    bus_ids = _lv_switchgear_bus_ids(snapshot, _lv_node_ids(snapshot))
    islands = [
        frozenset(component & bus_ids)
        for component in _lv_closed_components(snapshot)
        if component & bus_ids
    ]
    islands.sort(key=lambda buses: sorted(buses))
    return islands


def count_lv_islands(snapshot: TopologySnapshot) -> int:
    """Number of electrically separate LV islands (see :func:`lv_islands`)."""

    return len(lv_islands(snapshot))


def lv_island_of(snapshot: TopologySnapshot, node_id: str) -> frozenset[str]:
    """All LV node ids electrically bonded to ``node_id`` over closed switches.

    Returns the full LV connected component containing ``node_id``, or an empty
    frozenset if ``node_id`` is not an LV node.
    """

    for component in _lv_closed_components(snapshot):
        if node_id in component:
            return component
    return frozenset()


def closed_graph_has_cycle(snapshot: TopologySnapshot) -> bool:
    """Whether the closed-switch graph contains a cycle (undirected).

    Union-find over all CLOSED edges: an edge whose endpoints are already
    connected closes a loop. This is what makes ``tie_closed`` a real cycle
    rather than a tree.
    """

    parent: dict[str, str] = {}

    def find(node_id: str) -> str:
        parent.setdefault(node_id, node_id)
        root = node_id
        while parent[root] != root:
            root = parent[root]
        while parent[node_id] != root:
            parent[node_id], node_id = root, parent[node_id]
        return root

    for edge in snapshot.edges:
        if edge.switch_state is not SwitchState.CLOSED:
            continue
        a, b = find(edge.from_node_id), find(edge.to_node_id)
        if a == b:
            return True
        parent[a] = b
    return False
