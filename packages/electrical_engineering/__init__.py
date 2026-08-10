"""S3M ElectricalTwin -- electrical engineering calculations.

This package contains CALCULATIONS ONLY: standards-derived numeric constants,
advisory telemetry plausibility ranges, and the topology energization solver.
It defines no domain enumerations and no asset models -- those live in
:mod:`packages.canonical_electrical_model` and are imported from there.

Nothing in this package performs I/O, database or network access, and no value
here should be relied upon without independent verification by a licensed
professional engineer (see :mod:`packages.electrical_engineering.constants`).
"""

from __future__ import annotations

from . import constants, ranges, topology
from .ranges import PlausibilityRange, is_out_of_range
from .topology import (
    ENERGIZED_STATES,
    EnergizationResult,
    ImpactSet,
    downstream_impact,
    solve_energization,
)

__all__ = [
    "constants",
    "ranges",
    "topology",
    "PlausibilityRange",
    "is_out_of_range",
    "ENERGIZED_STATES",
    "EnergizationResult",
    "ImpactSet",
    "solve_energization",
    "downstream_impact",
]
