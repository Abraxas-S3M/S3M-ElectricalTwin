"""Topology models.

The electrical network is a *directed graph with live switching state*, not a
tree. Tie breakers and backfeed paths create genuine cycles, and the model is
built to express that: edges are directed (``from_node_id`` -> ``to_node_id``),
carry an independent live ``switch_state``, and there is no structural
constraint forbidding cycles.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field

from .common import CanonicalModel, Location
from .enums import (
    AssetType,
    Criticality,
    EdgeKind,
    SectorProfile,
    SourceType,
    SwitchState,
)
from .provenance import Provenance
from .ratings import EdgeImpedance, RatedData


class ElectricalNode(CanonicalModel):
    """A node in the electrical graph (bus, transformer, breaker, load, ...)."""

    id: str
    name: str
    asset_type: AssetType
    nominal_voltage_v: Optional[float] = Field(default=None, ge=0.0)
    phases: Literal[1, 3]
    parent_facility_id: str
    location: Optional[Location] = None
    criticality: Optional[Criticality] = None
    rated: Optional[RatedData] = None
    provenance: Provenance = Field(default_factory=Provenance)


class ElectricalEdge(CanonicalModel):
    """A directed connection between two nodes.

    ``switch_state`` is the live, observed state of the connection. It is a
    reported condition, never a command. ``switching_device_node_id`` optionally
    points at the node (breaker/switch) whose position governs this edge.
    """

    id: str
    from_node_id: str
    to_node_id: str
    edge_kind: EdgeKind
    switch_state: SwitchState = SwitchState.UNKNOWN
    switching_device_node_id: Optional[str] = None
    impedance: Optional[EdgeImpedance] = None
    ampacity_a: Optional[float] = Field(default=None, ge=0.0)
    provenance: Provenance = Field(default_factory=Provenance)


class SourceNode(CanonicalModel):
    """A supply source attached to a node.

    ``priority`` orders preferred supplies; a lower number is more preferred.
    """

    node_id: str
    source_type: SourceType
    rated_kva: Optional[float] = Field(default=None, ge=0.0)
    priority: int = Field(ge=0)


class Facility(CanonicalModel):
    """A facility (site) that owns a set of voltage levels and a topology.

    ``nominal_frequency_hz`` defaults to 60 Hz (the target market) but is fully
    configurable so adjacent 50 Hz markets are supported.
    """

    id: str
    name: str
    nominal_frequency_hz: float = Field(default=60.0, gt=0.0)
    nominal_voltage_levels: list[float] = Field(default_factory=list)
    timezone: str = "UTC"
    sector_profile: Optional[SectorProfile] = None


class TopologySnapshot(CanonicalModel):
    """An immutable-in-time capture of a facility's electrical graph."""

    snapshot_id: str
    facility_id: str
    captured_at: datetime
    nodes: list[ElectricalNode] = Field(default_factory=list)
    edges: list[ElectricalEdge] = Field(default_factory=list)
    sources: list[SourceNode] = Field(default_factory=list)
