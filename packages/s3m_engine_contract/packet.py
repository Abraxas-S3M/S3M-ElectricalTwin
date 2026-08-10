"""The packet the S3M engine reasons over.

An :class:`ElectricalTwinPacket` is a self-contained, hashable bundle of the
observed facts the engine is allowed to use for one unit of work. Crucially, the
``evidence_pool`` is the *only* set of facts the engine may cite: grounding is
enforced downstream against this pool.

Everything here is observe-only. The packet carries the canonical
:class:`ControlBoundary` to make the read-only posture explicit; it defines no
control-write field of its own. All data is synthetic.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from packages.canonical_electrical_model import (
    AnomalyResult,
    ControlBoundary,
    ElectricalReading,
    Evidence,
    HealthScore,
    PowerQualityEvent,
    TopologySnapshot,
)

from .routing import PacketClass, Urgency

#: Reference history depth (hours) at which the history component is fully
#: satisfied. One week of context is treated as complete for sufficiency.
_HISTORY_TARGET_HOURS: float = 168.0

#: Name of the hash field, excluded from the hash pre-image.
_HASH_FIELD = "packet_hash"


def _to_utc(value: datetime) -> datetime:
    """Normalise a datetime to UTC (treating naive values as UTC)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class ProvenanceSummary(BaseModel):
    """A compact summary of where the packet's data came from."""

    model_config = ConfigDict(extra="forbid")

    is_entirely_synthetic: bool = True
    source_count: int = Field(default=0, ge=0)
    notes: Optional[str] = None


class DataSufficiency(BaseModel):
    """How complete and trustworthy the packet's data is.

    The three ratios are in ``[0, 1]``; ``history_depth_hours`` is a duration.
    ``composite`` is a single derived score in ``[0, 1]`` and is computed from
    the components -- it is never assigned directly.
    """

    model_config = ConfigDict(extra="forbid")

    channel_coverage: float = Field(ge=0.0, le=1.0)
    quality_ratio: float = Field(ge=0.0, le=1.0)
    history_depth_hours: float = Field(ge=0.0)
    metering_completeness: float = Field(ge=0.0, le=1.0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def composite(self) -> float:
        """Mean of the four normalised components, in ``[0, 1]``."""
        history_score = min(1.0, self.history_depth_hours / _HISTORY_TARGET_HOURS)
        return (
            self.channel_coverage
            + self.quality_ratio
            + self.metering_completeness
            + history_score
        ) / 4.0


class ElectricalTwinPacket(BaseModel):
    """One unit of work presented to the S3M engine."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    packet_id: str
    packet_class: PacketClass
    urgency: Urgency
    created_at: datetime
    facility_id: str
    node_ids: list[str] = Field(default_factory=list)
    window_start: datetime
    window_end: datetime
    readings: list[ElectricalReading] = Field(default_factory=list)
    topology_snapshot: Optional[TopologySnapshot] = None
    # Populated by later work packages; empty in WP0.
    health_scores: list[HealthScore] = Field(default_factory=list)
    anomalies: list[AnomalyResult] = Field(default_factory=list)
    pq_events: list[PowerQualityEvent] = Field(default_factory=list)
    # The ONLY facts the engine may cite.
    evidence_pool: list[Evidence] = Field(default_factory=list)
    provenance_summary: ProvenanceSummary = Field(default_factory=ProvenanceSummary)
    data_sufficiency: DataSufficiency
    control_boundary: ControlBoundary = Field(
        default_factory=lambda: ControlBoundary(
            rationale="ElectricalTwinPacket is observe-only; the engine advises, never controls."
        )
    )
    packet_hash: str = ""

    @field_validator("created_at", "window_start", "window_end")
    @classmethod
    def _normalise_timestamps(cls, value: datetime) -> datetime:
        return _to_utc(value)


def compute_packet_hash(packet: ElectricalTwinPacket) -> str:
    """Return the SHA-256 hash of *packet* over canonical JSON.

    The pre-image is the packet serialised to JSON-compatible primitives with
    sorted keys and normalised (UTC, ISO-8601) timestamps, excluding the
    ``packet_hash`` field itself. Two packets with identical content therefore
    hash identically, and any single value change alters the hash.
    """
    data = packet.model_dump(mode="json")
    data.pop(_HASH_FIELD, None)
    canonical = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "ProvenanceSummary",
    "DataSufficiency",
    "ElectricalTwinPacket",
    "compute_packet_hash",
]
