"""Canonical electrical model.

Pydantic v2 models describing the *observed* and *rated* reality of an
electrical network: topology (a directed graph with live switching state),
telemetry, and the analytic contracts populated by later work packages.

By design the package is read-only: no model carries a setpoint, command,
write target, or control action, and :class:`ControlBoundary` encodes that
invariant explicitly.
"""

from __future__ import annotations

from .analytics import (
    AnomalyResult,
    ControlBoundary,
    Evidence,
    HealthContribution,
    HealthScore,
    PowerQualityEvent,
    RankedCause,
)
from .common import CanonicalModel, Location
from .enums import (
    AnomalyDomain,
    AssetType,
    ContributionDirection,
    Criticality,
    EdgeKind,
    HealthBand,
    ITICRegion,
    PhaseTag,
    PowerQualityEventType,
    Quality,
    SectorProfile,
    Severity,
    SourceType,
    SwitchState,
    ValidationState,
)
from .provenance import Provenance, Provenanced, ProvenanceSource
from .ratings import EdgeImpedance, RatedData
from .telemetry import ElectricalReading
from .topology import (
    ElectricalEdge,
    ElectricalNode,
    Facility,
    SourceNode,
    TopologySnapshot,
)

__all__ = [
    # common
    "CanonicalModel",
    "Location",
    # provenance
    "Provenance",
    "Provenanced",
    "ProvenanceSource",
    # enums
    "AnomalyDomain",
    "AssetType",
    "ContributionDirection",
    "Criticality",
    "EdgeKind",
    "HealthBand",
    "ITICRegion",
    "PhaseTag",
    "PowerQualityEventType",
    "Quality",
    "SectorProfile",
    "Severity",
    "SourceType",
    "SwitchState",
    "ValidationState",
    # ratings
    "EdgeImpedance",
    "RatedData",
    # topology
    "ElectricalEdge",
    "ElectricalNode",
    "Facility",
    "SourceNode",
    "TopologySnapshot",
    # telemetry
    "ElectricalReading",
    # analytics
    "AnomalyResult",
    "ControlBoundary",
    "Evidence",
    "HealthContribution",
    "HealthScore",
    "PowerQualityEvent",
    "RankedCause",
]
