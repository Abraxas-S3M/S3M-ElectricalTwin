"""Telemetry models.

Telemetry is strictly inbound: a reading is a measured observation from a
sensor. There is no channel here that could carry a value *to* an asset.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field

from .common import CanonicalModel
from .enums import PhaseTag, Quality
from .provenance import Provenance


class ElectricalReading(CanonicalModel):
    """A single measured telemetry sample for a node/channel."""

    node_id: str
    channel: str
    phase: Optional[PhaseTag] = None
    value: float
    unit: str
    timestamp: datetime
    provenance: Provenance = Field(default_factory=Provenance)
    quality: Quality = Quality.GOOD
    sensor_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
