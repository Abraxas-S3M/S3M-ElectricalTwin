"""Seeded scenarios with machine-readable ground truth.

A scenario pairs a fault injected into the reference telemetry with an exact,
benchmarkable label: where the fault is, when it starts, the earliest point a
correct detector could fire, which detector should fire, and which detectors
must stay silent. :func:`all_scenarios` returns the full catalogue.
"""

from __future__ import annotations

from .catalog import all_scenarios, scenario_by_id, scenario_ids
from .ground_truth import (
    ALL_DETECTORS,
    Detector,
    FaultCategory,
    ScenarioGroundTruth,
    all_detectors_except,
)

__all__ = [
    "all_scenarios",
    "scenario_by_id",
    "scenario_ids",
    "ALL_DETECTORS",
    "Detector",
    "FaultCategory",
    "ScenarioGroundTruth",
    "all_detectors_except",
]
