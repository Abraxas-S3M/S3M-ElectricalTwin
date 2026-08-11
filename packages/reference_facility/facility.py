"""The synthetic reference facility: metadata, asset inventory and base graph.

This module defines a single, fixed, entirely **synthetic** facility used to
demonstrate the platform end to end. Nothing here describes a real site, a real
customer, or a real product; every asset, rating and identifier is invented for
demonstration and is safe to publish.

The facility is a medium mixed-use building served from a single medium-voltage
utility service, with a standby generator, a dual-bus 480 V main switchboard
joined by a normally-open tie, two step-down transformers feeding 208 V
distribution panels, and a UPS carrying a life-safety critical panel. This shape
is deliberately rich enough to exercise primary/backup/UPS energization, an open
tie, backfeed through a closed tie, and ``UNKNOWN`` switch handling.

The base graph is expressed with the canonical :mod:`canonical_electrical_model`
types so it can be served directly by the read-only API. Topology *variants*
(see :mod:`reference_facility.topology`) are derived from this base by overriding
switch states only; the node and edge inventory never changes between variants.
"""

from __future__ import annotations

from packages.canonical_electrical_model import (
    AssetType,
    Criticality,
    EdgeKind,
    ElectricalEdge,
    ElectricalNode,
    Facility,
    Location,
    Provenance,
    ProvenanceSource,
    SectorProfile,
    SourceNode,
    SourceType,
    SwitchState,
)

#: Stable identifier for the one reference facility.
FACILITY_ID = "REF-FAC-001"

#: A note attached to every served payload, reinforcing that this is synthetic
#: demonstration data and any analytics derived from it are preliminary.
SYNTHETIC_NOTICE = (
    "All data for the reference facility is synthetic and invented for "
    "demonstration; it describes no real site or customer. Any analytics are "
    "preliminary and advisory only."
)

_SYNTHETIC_PROVENANCE = Provenance(
    source=ProvenanceSource.SYNTHETIC,
    method="reference_facility",
    reference=FACILITY_ID,
)


def _node(
    node_id: str,
    name: str,
    asset_type: AssetType,
    *,
    voltage: float | None,
    phases: int,
    criticality: Criticality | None = None,
    area: str | None = None,
) -> ElectricalNode:
    return ElectricalNode(
        id=node_id,
        name=name,
        asset_type=asset_type,
        nominal_voltage_v=voltage,
        phases=phases,  # type: ignore[arg-type]
        parent_facility_id=FACILITY_ID,
        criticality=criticality,
        location=Location(site="Reference Facility", area=area) if area else None,
        provenance=_SYNTHETIC_PROVENANCE,
    )


def _edge(
    edge_id: str,
    from_node_id: str,
    to_node_id: str,
    edge_kind: EdgeKind,
    switch_state: SwitchState,
    *,
    ampacity_a: float | None = None,
    switching_device_node_id: str | None = None,
) -> ElectricalEdge:
    return ElectricalEdge(
        id=edge_id,
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        edge_kind=edge_kind,
        switch_state=switch_state,
        switching_device_node_id=switching_device_node_id,
        ampacity_a=ampacity_a,
        provenance=_SYNTHETIC_PROVENANCE,
    )


# --- Base asset inventory ---------------------------------------------------

_BASE_NODES: tuple[ElectricalNode, ...] = (
    _node("UTIL-1", "Utility service", AssetType.UTILITY_SERVICE,
          voltage=13_800.0, phases=3, area="Service entrance"),
    _node("GEN-1", "Standby generator", AssetType.GENERATOR,
          voltage=480.0, phases=3, criticality=Criticality.HIGH, area="Generator yard"),
    _node("MV-XFMR", "Main step-down transformer", AssetType.TRANSFORMER,
          voltage=480.0, phases=3, criticality=Criticality.HIGH, area="Vault"),
    _node("MSB", "Main switchboard", AssetType.SWITCHBOARD,
          voltage=480.0, phases=3, criticality=Criticality.CRITICAL, area="Electrical room"),
    _node("BUS-A", "Distribution bus A", AssetType.BUS,
          voltage=480.0, phases=3, criticality=Criticality.HIGH, area="Electrical room"),
    _node("BUS-B", "Distribution bus B", AssetType.BUS,
          voltage=480.0, phases=3, criticality=Criticality.HIGH, area="Electrical room"),
    _node("XFMR-A", "Distribution transformer A", AssetType.TRANSFORMER,
          voltage=208.0, phases=3, criticality=Criticality.MEDIUM, area="Electrical room"),
    _node("XFMR-B", "Distribution transformer B", AssetType.TRANSFORMER,
          voltage=208.0, phases=3, criticality=Criticality.MEDIUM, area="Electrical room"),
    _node("PANEL-A", "Distribution panel A", AssetType.PANELBOARD,
          voltage=208.0, phases=3, criticality=Criticality.MEDIUM, area="Level 1"),
    _node("PANEL-B", "Distribution panel B", AssetType.PANELBOARD,
          voltage=208.0, phases=3, criticality=Criticality.MEDIUM, area="Level 2"),
    _node("UPS-1", "Uninterruptible power supply", AssetType.UPS,
          voltage=208.0, phases=3, criticality=Criticality.CRITICAL, area="Electrical room"),
    _node("PANEL-CRIT", "Life-safety panel", AssetType.PANELBOARD,
          voltage=208.0, phases=3, criticality=Criticality.LIFE_SAFETY, area="Level 1"),
    _node("LOAD-A1", "General load A1", AssetType.LOAD,
          voltage=208.0, phases=3, criticality=Criticality.LOW, area="Level 1"),
    _node("LOAD-A2", "General load A2", AssetType.LOAD,
          voltage=208.0, phases=3, criticality=Criticality.MEDIUM, area="Level 1"),
    _node("LOAD-B1", "General load B1", AssetType.LOAD,
          voltage=208.0, phases=3, criticality=Criticality.LOW, area="Level 2"),
    _node("LOAD-B2", "General load B2", AssetType.LOAD,
          voltage=208.0, phases=3, criticality=Criticality.MEDIUM, area="Level 2"),
    _node("LOAD-CRIT1", "Life-safety load", AssetType.LOAD,
          voltage=208.0, phases=3, criticality=Criticality.LIFE_SAFETY, area="Level 1"),
)

# --- Base edges (declared switch states describe the NORMAL configuration) --

_BASE_EDGES: tuple[ElectricalEdge, ...] = (
    _edge("E-UTIL-XFMR", "UTIL-1", "MV-XFMR", EdgeKind.SOURCE_CONNECTION,
          SwitchState.CLOSED, ampacity_a=1200.0),
    _edge("E-XFMR-MSB", "MV-XFMR", "MSB", EdgeKind.TRANSFORMER_WINDING,
          SwitchState.CLOSED, ampacity_a=2500.0),
    _edge("E-GEN-MSB", "GEN-1", "MSB", EdgeKind.SOURCE_CONNECTION,
          SwitchState.OPEN, ampacity_a=1600.0),
    _edge("E-MSB-BUSA", "MSB", "BUS-A", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=1600.0),
    _edge("E-MSB-BUSB", "MSB", "BUS-B", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=1600.0),
    _edge("E-TIE-AB", "BUS-A", "BUS-B", EdgeKind.TIE,
          SwitchState.OPEN, ampacity_a=1600.0),
    _edge("E-BUSA-XFMRA", "BUS-A", "XFMR-A", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=800.0),
    _edge("E-XFMRA-PANELA", "XFMR-A", "PANEL-A", EdgeKind.TRANSFORMER_WINDING,
          SwitchState.CLOSED, ampacity_a=800.0),
    _edge("E-BUSB-XFMRB", "BUS-B", "XFMR-B", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=800.0),
    _edge("E-XFMRB-PANELB", "XFMR-B", "PANEL-B", EdgeKind.TRANSFORMER_WINDING,
          SwitchState.CLOSED, ampacity_a=800.0),
    _edge("E-BUSA-UPS", "BUS-A", "UPS-1", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=400.0),
    _edge("E-UPS-CRIT", "UPS-1", "PANEL-CRIT", EdgeKind.SOURCE_CONNECTION,
          SwitchState.CLOSED, ampacity_a=400.0),
    _edge("E-PANELA-A1", "PANEL-A", "LOAD-A1", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=200.0),
    _edge("E-PANELA-A2", "PANEL-A", "LOAD-A2", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=200.0),
    _edge("E-PANELB-B1", "PANEL-B", "LOAD-B1", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=200.0),
    _edge("E-PANELB-B2", "PANEL-B", "LOAD-B2", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=200.0),
    _edge("E-PANELCRIT-C1", "PANEL-CRIT", "LOAD-CRIT1", EdgeKind.FEEDER,
          SwitchState.CLOSED, ampacity_a=200.0),
)

_BASE_SOURCES: tuple[SourceNode, ...] = (
    SourceNode(node_id="UTIL-1", source_type=SourceType.UTILITY, rated_kva=2500.0, priority=0),
    SourceNode(node_id="GEN-1", source_type=SourceType.GENERATOR, rated_kva=1250.0, priority=1),
    # The UPS is a standby island source: it is normally fed through, so it must
    # rank below the utility and the generator. If both are lost, it becomes the
    # only source and carries the critical panel.
    SourceNode(node_id="UPS-1", source_type=SourceType.UPS, rated_kva=300.0, priority=2),
)


def facility() -> Facility:
    """Return the metadata for the reference facility (a fresh instance)."""

    return Facility(
        id=FACILITY_ID,
        name="S3M Reference Facility (synthetic)",
        nominal_frequency_hz=60.0,
        nominal_voltage_levels=[13_800.0, 480.0, 208.0],
        timezone="UTC",
        sector_profile=SectorProfile.MIXED_USE,
    )


def base_nodes() -> list[ElectricalNode]:
    """Return the full asset inventory (a fresh list of fresh instances)."""

    return [n.model_copy(deep=True) for n in _BASE_NODES]


def base_edges() -> list[ElectricalEdge]:
    """Return the base edges in their NORMAL switch configuration."""

    return [e.model_copy(deep=True) for e in _BASE_EDGES]


def base_sources() -> list[SourceNode]:
    """Return the energization sources for the facility."""

    return [s.model_copy(deep=True) for s in _BASE_SOURCES]
