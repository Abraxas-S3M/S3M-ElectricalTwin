"""Reference facility: a synthetic site, its telemetry generator, and the
seeded scenarios that inject faults into it.

This package is the benchmarkable substrate for the whole platform. It exposes:

* a fixed synthetic facility (:func:`reference_topology`, :func:`facility_node_ids`);
* a deterministic telemetry generator (:func:`generate`) that injects a chosen
  scenario's fault; and
* thirteen scenarios (:func:`all_scenarios`) each carrying machine-readable
  ground truth so downstream detectors can be scored rather than eyeballed.

All data here is synthetic. Nothing in this package reads from or writes to any
real asset; it produces observations only.
"""

from __future__ import annotations

from .facility import (
    FACILITY_ID,
    POWER_HIERARCHY,
    SIM_START,
    SIM_STEP,
    SIM_STEPS,
    facility_node_ids,
    metered_parents,
    node_exists,
    reference_facility,
    reference_topology,
    sim_index,
    sim_timestamp,
)
from .scenarios import (
    ALL_DETECTORS,
    Detector,
    FaultCategory,
    ScenarioGroundTruth,
    all_scenarios,
    scenario_by_id,
    scenario_ids,
)
from .telemetry import (
    GeneratedTelemetry,
    generate,
    max_power_imbalance_kw,
    power_balance_breaks_at,
)

__all__ = [
    # facility
    "FACILITY_ID",
    "POWER_HIERARCHY",
    "SIM_START",
    "SIM_STEP",
    "SIM_STEPS",
    "facility_node_ids",
    "metered_parents",
    "node_exists",
    "reference_facility",
    "reference_topology",
    "sim_index",
    "sim_timestamp",
    # scenarios
    "ALL_DETECTORS",
    "Detector",
    "FaultCategory",
    "ScenarioGroundTruth",
    "all_scenarios",
    "scenario_by_id",
    "scenario_ids",
    # telemetry
    "GeneratedTelemetry",
    "generate",
    "max_power_imbalance_kw",
    "power_balance_breaks_at",
]
