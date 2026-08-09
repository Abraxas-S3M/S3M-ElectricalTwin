"""S3M ElectricalTwin -- electrical engineering package.

Pure-Python domain model, standards-derived numeric constants, advisory
telemetry plausibility ranges and the topology energization solver.

Nothing in this package performs I/O, database or network access, and no value
here should be relied upon without independent verification by a licensed
professional engineer (see :mod:`electrical_engineering.constants`).
"""

from __future__ import annotations

from . import constants, ranges, topology
from .enums import (
    ENERGIZED_STATES,
    Criticality,
    EnergizationState,
    SourceType,
    SwitchState,
    TelemetryChannel,
)
from .models import (
    Edge,
    EnergizationResult,
    ImpactSet,
    Node,
    SourceNode,
)
from .ranges import PlausibilityRange, is_out_of_range
from .topology import downstream_impact, solve_energization

__all__ = [
    "constants",
    "ranges",
    "topology",
    "SwitchState",
    "SourceType",
    "EnergizationState",
    "ENERGIZED_STATES",
    "Criticality",
    "TelemetryChannel",
    "Node",
    "SourceNode",
    "Edge",
    "EnergizationResult",
    "ImpactSet",
    "PlausibilityRange",
    "is_out_of_range",
    "solve_energization",
    "downstream_impact",
]
"""Electrical engineering analytics for S3M ElectricalTwin (advisory, read-only).

Placeholder package. Analytics added here are preliminary and advisory only;
nothing in this package may command or actuate any control system or field
device.
"""
