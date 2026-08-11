"""S3M ElectricalTwin -- reference facility package.

A single, fixed, entirely **synthetic** demonstration facility plus the
deterministic replay engine that regenerates its telemetry on demand.

The package ships no telemetry data and has no storage or persistence layer:
everything is computed when requested and proven reproducible by hash. Nothing
here performs I/O, and nothing here writes to, commands, or actuates any control
system or field device -- the platform is advisory and read-only.
"""

from __future__ import annotations

from .energization import (
    energization,
    energization_rows,
    energize_snapshot,
    snapshot_to_engineering,
)
from .facility import (
    FACILITY_ID,
    SYNTHETIC_NOTICE,
    base_edges,
    base_nodes,
    base_sources,
    facility,
)
from .replay import (
    ReplayManifest,
    ReplayResult,
    replay,
    replay_manifest,
)
from .scenarios import (
    GroundTruth,
    MonitoredPoint,
    Perturbation,
    Scenario,
    SwitchingEvent,
    UnknownScenarioError,
    all_scenarios,
    get_scenario,
    scenario_ids,
)
from .topology import (
    TOPOLOGY_VARIANTS,
    UnknownVariantError,
    build_snapshot,
    topology,
)

__all__ = [
    # facility
    "FACILITY_ID",
    "SYNTHETIC_NOTICE",
    "facility",
    "base_nodes",
    "base_edges",
    "base_sources",
    # topology
    "TOPOLOGY_VARIANTS",
    "UnknownVariantError",
    "topology",
    "build_snapshot",
    # energization
    "energization",
    "energization_rows",
    "energize_snapshot",
    "snapshot_to_engineering",
    # scenarios
    "Scenario",
    "GroundTruth",
    "MonitoredPoint",
    "Perturbation",
    "SwitchingEvent",
    "UnknownScenarioError",
    "all_scenarios",
    "get_scenario",
    "scenario_ids",
    # replay
    "ReplayResult",
    "ReplayManifest",
    "replay",
    "replay_manifest",
]
