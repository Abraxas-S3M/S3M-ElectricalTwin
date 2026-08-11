"""S3M ElectricalTwin -- electrical engineering package.

Standards-derived numeric constants, advisory telemetry plausibility ranges and
the topology energization solver. The domain vocabulary (enumerations) and the
network model (nodes, edges, sources) are owned by
:mod:`packages.canonical_electrical_model`; this package consumes them and adds
only the analytic *outputs* (see :mod:`results`).

Nothing in this package performs I/O, database or network access, and no value
here should be relied upon without independent verification by a licensed
professional engineer (see :mod:`electrical_engineering.constants`).
"""

from __future__ import annotations

from packages.canonical_electrical_model import (
    Criticality,
    EnergizationState,
    SourceType,
    SwitchState,
    TelemetryChannel,
)

from . import constants, ranges, topology
from .ranges import PlausibilityRange, is_out_of_range
from .results import ENERGIZED_STATES, EnergizationResult, ImpactSet
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
    "EnergizationResult",
    "ImpactSet",
    "PlausibilityRange",
    "is_out_of_range",
    "solve_energization",
    "downstream_impact",
]
