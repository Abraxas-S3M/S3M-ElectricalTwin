"""The packet the S3M engines consume: :class:`ElectricalTwinPacket`.

A packet is a self-contained, immutable-by-convention bundle of everything an
engine is permitted to see for a single unit of work. It is deliberately
*closed world*: the ``evidence_pool`` is the ONLY set of facts an engine may
cite. Nothing here invokes a language model and all data is synthetic.

The packet carries a ``packet_hash`` computed with :func:`compute_packet_hash`,
a sha256 over the canonical JSON of the packet (sorted keys, normalised
timestamps) excluding the hash field itself. Identical packets hash identically;
changing any single value changes the hash.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field

from .routing import PacketClass, Urgency

__all__ = [
    "PacketClass",
    "Urgency",
    "Reading",
    "TopologyNode",
    "TopologyEdge",
    "TopologySnapshot",
    "Evidence",
    "ProvenanceSummary",
    "DataSufficiency",
    "ControlBoundary",
    "ElectricalTwinPacket",
    "compute_packet_hash",
    "HISTORY_TARGET_HOURS",
]

# Reference history depth (hours) used to normalise ``history_depth_hours`` into
# a 0..1 contribution to the data-sufficiency composite. One week of context.
HISTORY_TARGET_HOURS: float = 168.0


class Reading(BaseModel):
    """A single synthetic measurement drawn from a node channel."""

    model_config = ConfigDict(extra="forbid")

    node_id: str
    channel: str
    timestamp: datetime
    value: float
    unit: str
    quality: float = Field(default=1.0, ge=0.0, le=1.0)


class TopologyNode(BaseModel):
    """A node in the electrical topology snapshot."""

    model_config = ConfigDict(extra="forbid")

    node_id: str
    node_type: str
    label: str | None = None


class TopologyEdge(BaseModel):
    """A directed connection between two topology nodes."""

    model_config = ConfigDict(extra="forbid")

    from_node: str
    to_node: str
    edge_type: str


class TopologySnapshot(BaseModel):
    """The electrical topology as observed at ``captured_at``."""

    model_config = ConfigDict(extra="forbid")

    captured_at: datetime
    nodes: list[TopologyNode] = Field(default_factory=list)
    edges: list[TopologyEdge] = Field(default_factory=list)


class Evidence(BaseModel):
    """A single citable fact.

    The packet's ``evidence_pool`` is the closed set of facts an engine may
    cite; every :class:`Evidence` carries a stable ``evidence_id`` that cards
    reference from their claims.
    """

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    kind: str
    statement: str
    node_ids: list[str] = Field(default_factory=list)
    value: float | None = None
    unit: str | None = None
    observed_at: datetime | None = None
    source: str = "synthetic"


class ProvenanceSummary(BaseModel):
    """Where the packet's data came from."""

    model_config = ConfigDict(extra="forbid")

    is_entirely_synthetic: bool = True
    generator: str = "wp0-synthetic-generator"
    source_count: int = Field(default=0, ge=0)
    notes: str | None = None


class DataSufficiency(BaseModel):
    """How complete and trustworthy the packet's data is.

    ``composite`` is COMPUTED from the four inputs and is never directly
    assignable. ``history_depth_hours`` is normalised against
    :data:`HISTORY_TARGET_HOURS` before contributing to the composite.
    """

    model_config = ConfigDict(extra="forbid")

    channel_coverage: float = Field(ge=0.0, le=1.0)
    quality_ratio: float = Field(ge=0.0, le=1.0)
    history_depth_hours: float = Field(ge=0.0)
    metering_completeness: float = Field(ge=0.0, le=1.0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def composite(self) -> float:
        """Equal-weighted mean of the four (normalised) sufficiency inputs."""

        history_component = min(self.history_depth_hours / HISTORY_TARGET_HOURS, 1.0)
        return round(
            (
                self.channel_coverage
                + self.quality_ratio
                + self.metering_completeness
                + history_component
            )
            / 4.0,
            6,
        )


class ControlBoundary(BaseModel):
    """The advisory-only boundary of the platform.

    S3M never actuates equipment. This model encodes that contract: it is
    read-only, exposes no control-write path, and enforces that invariant via a
    validator so a control-write path can never be represented.
    """

    model_config = ConfigDict(extra="forbid")

    read_only: bool = True
    write_path_present: bool = False
    permitted_operations: list[str] = Field(
        default_factory=lambda: ["read", "recommend"]
    )
    description: str = "Advisory-only; no control-write path exists."

    def model_post_init(self, __context: Any) -> None:  # noqa: D401
        if self.write_path_present or not self.read_only:
            raise ValueError(
                "ControlBoundary must remain advisory-only: no control-write "
                "path is permitted."
            )


class ElectricalTwinPacket(BaseModel):
    """The unit of work handed to an S3M engine.

    In Work Package 0 the derived analytical fields (``health_scores``,
    ``anomalies``, ``pq_events``) are always empty; they are declared here so
    the contract is stable for later work packages.
    """

    model_config = ConfigDict(extra="forbid")

    packet_id: str
    packet_class: PacketClass
    urgency: Urgency
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    facility_id: str
    node_ids: list[str] = Field(default_factory=list)
    window_start: datetime
    window_end: datetime
    readings: list[Reading] = Field(default_factory=list)
    topology_snapshot: TopologySnapshot
    health_scores: list[Any] = Field(default_factory=list)
    anomalies: list[Any] = Field(default_factory=list)
    pq_events: list[Any] = Field(default_factory=list)
    evidence_pool: list[Evidence] = Field(default_factory=list)
    provenance_summary: ProvenanceSummary
    data_sufficiency: DataSufficiency
    control_boundary: ControlBoundary = Field(default_factory=ControlBoundary)
    packet_hash: str = ""


def _normalise_timestamp(value: datetime) -> str:
    """Render a datetime as a normalised UTC ISO-8601 string.

    Naive datetimes are assumed to be UTC; aware datetimes are converted to
    UTC. Microsecond precision is always emitted so equal instants serialise
    identically regardless of their original representation.
    """

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    return value.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def _normalise(obj: Any) -> Any:
    """Recursively canonicalise a dumped packet for hashing."""

    if isinstance(obj, dict):
        return {key: _normalise(val) for key, val in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalise(val) for val in obj]
    if isinstance(obj, datetime):
        return _normalise_timestamp(obj)
    if isinstance(obj, Enum):
        return obj.value
    return obj


def compute_packet_hash(packet: ElectricalTwinPacket) -> str:
    """Return the sha256 hex digest of a packet's canonical content.

    The digest is taken over canonical JSON with sorted keys and normalised
    timestamps, and it deliberately EXCLUDES the ``packet_hash`` field itself so
    the hash of a packet is independent of any hash already stored on it.
    """

    data = packet.model_dump(mode="python")
    data.pop("packet_hash", None)
    canonical = json.dumps(
        _normalise(data),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
